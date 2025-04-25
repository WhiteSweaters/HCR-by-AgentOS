import streamlit as st
import requests
import logging
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic


st.set_page_config(
    page_title="Hospitals",
    page_icon="🏥",
)


# data = {
#     'latitude': [30.579121999999995, 30.582869000000002, 30.553873000000003, 30.535321000000007, 30.517218000000028],
#     'longitude': [114.26234900000009, 114.27413299999989, 114.353838, 114.298947, 114.41445299999998],
#     'name': ['同济医院', '协和医院', '中南医院', '人民医院', '华中科技大学校医院']
# }
# st.map(data, use_container_width=True)


BAIDU_API_AK = "your_baidu_api_key_here" 


st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .sidebar .sidebar-content {
        background: #ffffff;
        box-shadow: 5px 0 15px rgba(0,0,0,0.1);
    }
    h1 {
        color: #2c3e50;
    }
    .st-bq {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


# --------------------- Functions ---------------------
def get_client_ip():
    """Get client's real IP (prioritize domestic services)"""
    services = [
        {'url': 'https://www.taobao.com/help/getip.php', 'pattern': 'ip', 'type': 'text'},
        {'url': 'https://ip.360.cn/IPShare/info', 'key': 'ip'},
        {'url': 'https://ipinfo.io/json', 'key': 'ip'},
    ]
    for service in services:
        try:
            response = requests.get(service['url'], timeout=3)
            response.raise_for_status()
            if 'type' in service and service['type'] == 'text':
                ip = response.text.strip().split('=')[-1].strip("'")
                if ip.count('.') == 3:
                    return ip
            else:
                data = response.json()
                if 'key' in service:
                    return data.get(service['key'], '').split(',')[0].strip()       
        except Exception as e:
            logging.warning(f"Service {service['url']} failed: {str(e)}")
            continue   
    logging.error("All IP services unavailable")
    return None


def get_location(ip):
    """High-precision IP positioning using Baidu Map API"""
    try:
        url = f"https://api.map.baidu.com/location/ip?ip={ip}&ak={BAIDU_API_AK}&coor=bd09ll"
        response = requests.get(url, timeout=3)
        data = response.json()
        if data['status'] == 0:
            return (
                data['content']['point']['y'], 
                data['content']['point']['x'],
                data['content'].get('accuracy', 'City-level positioning')
            )
        return None, None, "Positioning failed"
    except Exception as e:
        logging.error(f"Positioning request failed: {str(e)}")
        return None, None, "Service exception"


def get_hospitals(lat, lon, radius=20000):
    """Get hospital data via Overpass API"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node["amenity"="hospital"](around:{radius},{lat},{lon});
    out body;
    """
    try:
        response = requests.post(overpass_url, data=query, timeout=10)
        response.raise_for_status()
        data = response.json()
        hospitals = []
        for element in data['elements']:
            hospitals.append({
                'name': element['tags'].get('name', 'Unknown Hospital'),
                'lat': element['lat'],
                'lon': element['lon'],
            })
        return pd.DataFrame(hospitals)
    except Exception as e:
        st.error(f"Failed to get hospital data: {str(e)}")
        return pd.DataFrame()


def calculate_distance(row, user_loc):
    """Calculate distance between hospital and user (km)"""
    hospital_loc = (row['lat'], row['lon'])
    return geodesic(user_loc, hospital_loc).km


# --------------------- Page Layout ---------------------
st.title("🏥 Nearby Hospital")
st.write("Medical resource query system based on precise positioning")
# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings Panel")
    # Manual positioning toggle
    manual_mode = st.checkbox("Manual Positioning Mode", help="Enable when automatic positioning is inaccurate")
    if manual_mode:
        default_lat, default_lon = 30.518371, 114.424921  # Wuhan 
        lat = st.number_input("Latitude", value=default_lat, format="%.6f")
        lon = st.number_input("Longitude", value=default_lon, format="%.6f")
        user_loc = (lat, lon)
        accuracy = "Manual location"
    else:
        # Automatic positioning
        with st.spinner('Fetching location information...'):
            ip = get_client_ip()
            lat, lon, accuracy = get_location(ip) if ip else (None, None, "Positioning failed")
            user_loc = (lat, lon) if lat and lon else None
    # Search parameters
    search_radius = st.slider("Search radius (kilometers)", 1, 50, 20)
    min_distance = st.slider("Display nearest hospitals count", 1, 50, 25)


# --------------------- Location Display ---------------------
if manual_mode:
    st.success("✅ Manual positioning mode enabled")
else:
    st.write(f"**Detected IP Address:** `{ip if ip else 'Unknown'}`")
if user_loc:
    st.write(f"""
    **Current Location Information**
    - Latitude: `{user_loc[0]:.6f}`
    - Longitude: `{user_loc[1]:.6f}`
    - Positioning Accuracy: `{accuracy}`
    """)
else:
    st.error("Unable to obtain location information. Please try:")
    st.markdown("1. Check network connection\n2. Enable manual positioning mode\n3. Refresh page")
    st.stop()


# --------------------- Data Retrieval ---------------------
with st.spinner(f'Searching for hospitals within {search_radius} kilometers...'):
    hospitals_df = get_hospitals(*user_loc, search_radius*1000)
    if hospitals_df.empty:
        st.warning("⚠️ No medical institutions found within the current range")
        st.stop()
    # Calculate distances
    hospitals_df['distance'] = hospitals_df.apply(
        lambda row: calculate_distance(row, user_loc), 
        axis=1
    )
    hospitals_df = hospitals_df.sort_values('distance').head(min_distance)


# --------------------- Visualization ---------------------
# Stats cards
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🏥 Medical Institutions", len(hospitals_df))
with col2:
    st.metric("📏 Nearest Distance", f"{hospitals_df['distance'].min():.2f} km")
with col3:
    st.metric("📏 Farthest Distance", f"{hospitals_df['distance'].max():.2f} km")
# Map visualization
map_layers = [
    pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{'lat': user_loc[0], 'lon': user_loc[1]}]),
        get_position='[lon, lat]',
        get_color='[255, 0, 0, 200]',
        get_radius=200,
        pickable=True
    ),
    pdk.Layer(
        "ScatterplotLayer",
        data=hospitals_df,
        get_position='[lon, lat]',
        get_color='[0, 128, 255, 200]',
        get_radius=150,
        pickable=True
    )
]
st.pydeck_chart(pdk.Deck(
    map_style='road',
    initial_view_state=pdk.ViewState(
        latitude=user_loc[0],
        longitude=user_loc[1],
        zoom=12,
        pitch=50
    ),
    layers=map_layers,
    tooltip={
        'html': '<b>{name}</b><br/>Distance: {distance} km',
        'style': {'color': 'white'}
    }
))
# Data table
st.subheader("📋 Hospital Details")
st.dataframe(
    hospitals_df[['name', 'distance']].rename(
        columns={'name':'Name', 'distance':'Distance'}
    ),
    height=400,
    column_config={
        "Name": st.column_config.TextColumn(
            width="medium",
            text_align="center"
        ),
        "Distance": st.column_config.NumberColumn(
            format="%.2f km",
            width="medium",
            text_align="center" 
        )
    }
)
# Refresh button
if st.button("🔄 Refresh Data"):
    st.experimental_rerun()
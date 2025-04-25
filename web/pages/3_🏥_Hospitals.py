import streamlit as st
import requests
import logging
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic
BAIDU_API_AK = "kfLxkGbOE95apSymbmlTBLRjIt4Jsd7U"


st.set_page_config(
    page_title="Hospitals",
    page_icon="🏥",
)


# --------------------- Functions ---------------------
def get_client_ip():
    """获取客户端IP（优先国内服务）"""
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
    """使用百度地图API进行高精度IP定位"""
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
        return None, None, "Location failed"
    except Exception as e:
        logging.error(f"Location request failed: {str(e)}")
        return None, None, "Service exception"


def geocode_address(address):
    """地址地理编码（使用百度地图API）"""
    try:
        url = f"http://api.map.baidu.com/geocoding/v3/?address={address}&output=json&ak={BAIDU_API_AK}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['status'] == 0:
            location = data['result']['location']
            return location['lat'], location['lng']
        return None, None
    except Exception as e:
        logging.error(f"Geocoding failed: {str(e)}")
        return None, None


def get_hospitals(lat, lon, radius=20000):
    """通过Overpass API获取医院数据"""
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
                'name': element['tags'].get('name', '未知医院'),
                'lat': element['lat'],
                'lon': element['lon'],
            })
        return pd.DataFrame(hospitals)
    except Exception as e:
        st.error(f"Failed to get hospital data: {str(e)}")
        return pd.DataFrame()


def calculate_distance(row, user_loc):
    """计算医院与用户的距离（千米）"""
    hospital_loc = (row['lat'], row['lon'])
    return geodesic(user_loc, hospital_loc).km


# --------------------- Page Layout ---------------------
st.title("Nearby Hospital")
st.write("A Medical Resource Query System Based on Precise Positioning")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings Panel")
    user_loc = None
    accuracy = ""
    # Manual positioning toggle
    # manual_mode = st.checkbox("Manual Positioning Mode", help="Enable when automatic positioning is inaccurate")
    mode = st.radio("Mode",
                   ["Auto_Mode", "Manual_Mode"],
                   index=0,
                   help="Select Mode",
                   horizontal=True)  # 水平排列选项
    # Search parameters
    search_radius = st.slider("Search Radius (km)", 1, 50, 20)
    min_distance = st.slider("Number of Nearest Hospitals to Display", 1, 50, 25)
    st.markdown("------")
    if mode == "Manual_Mode":
        address = st.text_input("Please enter a detailed address", 
                              placeholder="eg:武汉市洪山区华中科技大学",)
        if st.button("📍 Geocode Address"):
            with st.spinner('Geocoding address...'):
                lat, lon = geocode_address(address)
                if lat and lon:
                    user_loc = (lat, lon)
                    accuracy = "Manual positioning"
                    st.success("Address geocoding successful!")
                else:
                    st.error("Geocoding failed, please check input format")
    else:
        # Automatic positioning
        with st.spinner('Fetching location information...'):
            ip = get_client_ip()
            if ip:
                lat, lon, accuracy = get_location(ip)
                user_loc = (lat, lon) if lat and lon else None
            else:
                user_loc = None
                accuracy = "Location failed"
    # Display location information
    if user_loc:
        try:
            lat = float(user_loc[0])
            lon = float(user_loc[1])
            st.subheader("📍 Location Information")
            st.write(f"""
            - Latitude: `{lat:.6f}`
            - Longitude: `{lon:.6f}`
            - Accuracy: `{accuracy}`
            """)
        except (TypeError, ValueError) as e:
            st.error(f"Coordinate format error: {str(e)}")
            st.stop()
    else:
        st.stop()


# --------------------- Data Fetching ---------------------
with st.spinner(f'Searching for hospitals within {search_radius} km radius...'):
    hospitals_df = get_hospitals(*user_loc, search_radius*1000)
    if hospitals_df.empty:
        st.warning("⚠️ No medical institutions found within current range")
        st.stop()
    # Calculate distances
    hospitals_df['distance'] = hospitals_df.apply(
        lambda row: calculate_distance(row, user_loc), 
        axis=1
    )
    hospitals_df = hospitals_df.sort_values('distance').head(min_distance)


# --------------------- Content Display ---------------------
if mode == "Manual_Mode":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Medical Institutions", len(hospitals_df), border=True)
    with col2:
        st.metric("Nearest Distance", f"{hospitals_df['distance'].min():.2f} km", border=True)
    with col3:
        st.metric("Farthest Distance", f"{hospitals_df['distance'].max():.2f} km", border=True)
    # Map visualization
    st.subheader("🗺️ Hospital Map")
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
    display_df = hospitals_df[['name', 'distance']].rename(
        columns={'name': 'Hospital Name', 'distance': 'Distance (km)'}
        )
    display_df['Distance (km)'] = display_df['Distance (km)'].round(2)
    st.dataframe(
        display_df,
        height=400,
        use_container_width=True,
        column_config={
            "Hospital Name": st.column_config.TextColumn(
                width="medium",
                help="Medical institution name"
            ),
            "Distance (km)": st.column_config.NumberColumn(
                format="%.2f km",
                help="Distance from your location"
            )
        },
        hide_index=True
    )
else:
    # Automatic mode shows table in expander
    with st.expander(f"🏥 Nearby Hospitals ({len(hospitals_df)} found)", expanded=True):
        display_df = hospitals_df[['name', 'distance']].rename(
            columns={'name': 'Hospital Name', 'distance': 'Distance (km)'}
        )
        display_df['Distance (km)'] = display_df['Distance (km)'].round(2)
        st.dataframe(
            display_df,
            height=400,
            use_container_width=True,
            column_config={
                "Hospital Name": st.column_config.TextColumn(
                    width="medium",
                    help="Medical institution name"
                ),
                "Distance (km)": st.column_config.NumberColumn(
                    format="%.2f km",
                    help="Distance from your location"
                )
            },
            hide_index=True
        )
        st.caption(f"""
        Summary: 
        - Average Distance: {display_df['Distance (km)'].mean():.2f} km
        - Nearest Hospital: {display_df['Distance (km)'].min():.2f} km
        - Coverage Radius: {display_df['Distance (km)'].max():.2f} km
        """)
# Refresh button
if st.button("🔄 Refresh Data"):
    st.rerun()
from fpdf import FPDF
import datetime

def generate_report(user_info: dict, recommendations: str, output_path: str):
    """
    生成体检报告 PDF。
    :param user_info: {'id':..., 'gender':..., 'age':..., 'height':..., 'weight':..., 'history':..., 'symptoms':...}
    :param recommendations: [{'package_name':..., 'score':..., 'items':[...]}, ...]
    :param output_path: PDF 文件保存路径
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(0, 10, "体检推荐", ln=True, align="C")
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(0, 8, f"生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)

    # 用户信息
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "一、用户基本信息", ln=True)
    pdf.set_font("Arial", size=12)
    for k, v in user_info.items():
        pdf.cell(0, 7, f"{k}：{v}", ln=True)
    pdf.ln(5)

    # 推荐结果
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "二、推荐体检方案", ln=True)
    pdf.set_font("Arial", size=12)
    lines = recommendations.splitlines()
    for line in lines:
        pdf.multi_cell(0, 7, line)
        pdf.ln(2)

    # 输出
    pdf.output(output_path)

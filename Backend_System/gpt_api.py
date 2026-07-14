from openai import OpenAI

import os
from dotenv import load_dotenv

load_dotenv()

def get_company_description(stock_name):
    
    client = OpenAI()
    if not OpenAI:
        raise EnvironmentError("กรุณาตรวจสอบ API Key ในไฟล์ .env หรือไม่ได้ส่งผ่านพารามิเตอร์")
    
    prompt = f"""
    กรุณาอธิบายบริษัท {stock_name} ประกอบธุรกิจอะไร มีผลิตภัณฑ์หรือบริการอะไรบ้าง
    และมีจุดเด่นหรือความได้เปรียบทางการแข่งขันอย่างไร มีรายละเอียดอะไรที่สำคัญ เช่น
    รายได้หลัก สินค้ามีอะไรพัฒนาใหม่บ้าง จุดเด่น ขอให้ตอบเป็นภาษาไทย
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}"
    

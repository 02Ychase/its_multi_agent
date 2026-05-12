"""
初始化售后相关的示例数据。
运行方式: cd backend/app && python scripts/init_after_sales_data.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.database_pool import DatabasePool


def seed_data():
    conn = DatabasePool.get_connection()
    try:
        cursor = conn.cursor()

        # 订单数据
        cursor.execute("SELECT COUNT(*) FROM orders")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO orders (order_id, product, status, logistics, estimated_delivery, purchase_date, amount) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    ("ORD20240512001", "ThinkPad X1 Carbon Gen 11", "已发货，运输中", "顺丰快递 SF1234567890", "2024年5月15日", "2024-05-12", 9999.00),
                    ("ORD20240510002", "ThinkPad T14s Gen 4", "已签收", "京东物流 JD0987654321", "已送达", "2024-05-10", 7499.00),
                    ("ORD20240508003", "Legion Y9000P 2024", "仓库处理中", "待发货", "预计2024年5月18日发货", "2024-05-08", 8999.00),
                    ("ORD20240601004", "小米14 Pro", "已签收", "中通快递 ZTO1122334455", "已送达", "2024-06-01", 4999.00),
                    ("ORD20240615005", "华为MatePad Pro 13.2", "已发货，运输中", "韵达快递 YD5566778899", "2024年6月18日", "2024-06-15", 5699.00),
                ]
            )
            print("订单数据已插入")

        # 保修数据
        cursor.execute("SELECT COUNT(*) FROM warranty_records")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO warranty_records (product, purchase_date, warranty_end, warranty_type, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    ("ThinkPad X1 Carbon Gen 11", "2024-01-10", "2027-01-10", "整机1年 + 主要部件延保至3年", "在保修期内"),
                    ("ThinkPad T14s Gen 4", "2023-06-15", "2024-06-15", "整机1年", "已过保"),
                    ("Legion Y9000P 2024", "2024-03-20", "2027-03-20", "整机1年 + 主要部件延保至3年", "在保修期内"),
                    ("小米14 Pro", "2024-06-01", "2025-06-01", "整机1年", "在保修期内"),
                    ("华为MatePad Pro 13.2", "2024-06-15", "2025-06-15", "整机1年", "在保修期内"),
                ]
            )
            print("保修数据已插入")

        # 维修工单数据
        cursor.execute("SELECT COUNT(*) FROM repair_tickets")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO repair_tickets (repair_id, product, issue, status, received_date, estimated_completion, technician_note) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    ("RPR20240501", "ThinkPad X1 Carbon Gen 11", "屏幕显示异常，出现彩色条纹", "维修中", "2024-05-01", "2024-05-16", "已确认为屏幕排线故障，配件已到，预计2个工作日完成"),
                    ("RPR20240428", "Legion Y9000P 2024", "键盘部分按键失灵", "待取机", "2024-04-28", "2024-05-10", "已更换键盘模块，测试正常，请携带取机凭证到店取机"),
                    ("RPR20240505", "ThinkPad T14s Gen 4", "电池无法充电", "已接单，等待检测", "2024-05-05", "2024-05-20", "设备已收到，排队等待工程师检测"),
                    ("RPR20240610", "小米14 Pro", "屏幕碎裂", "维修中", "2024-06-10", "2024-06-17", "屏幕总成已到货，更换中"),
                ]
            )
            print("维修工单数据已插入")

        conn.commit()
        print("所有售后数据初始化完成")
    finally:
        conn.close()


if __name__ == "__main__":
    from repositories.after_sales_repository import init_after_sales_tables
    init_after_sales_tables()
    seed_data()

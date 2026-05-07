from agents import function_tool
from infrastructure.logging.logger import logger

# 模拟订单数据库
MOCK_ORDERS = {
    "ORD20240512001": {
        "order_id": "ORD20240512001",
        "product": "ThinkPad X1 Carbon Gen 11",
        "status": "已发货，运输中",
        "logistics": "顺丰快递 SF1234567890",
        "estimated_delivery": "2024年5月15日",
        "purchase_date": "2024-05-12",
    },
    "ORD20240510002": {
        "order_id": "ORD20240510002",
        "product": "ThinkPad T14s Gen 4",
        "status": "已签收",
        "logistics": "京东物流 JD0987654321",
        "estimated_delivery": "已送达",
        "purchase_date": "2024-05-10",
    },
    "ORD20240508003": {
        "order_id": "ORD20240508003",
        "product": "Legion Y9000P 2024",
        "status": "仓库处理中",
        "logistics": "待发货",
        "estimated_delivery": "预计2024年5月18日发货",
        "purchase_date": "2024-05-08",
    },
}

# 模拟保修数据库
MOCK_WARRANTY = {
    "ThinkPad X1 Carbon": {
        "product": "ThinkPad X1 Carbon Gen 11",
        "purchase_date": "2024-01-10",
        "warranty_end": "2027-01-10",
        "warranty_type": "整机1年 + 主要部件延保至3年",
        "status": "在保修期内",
    },
    "ThinkPad T14s": {
        "product": "ThinkPad T14s Gen 4",
        "purchase_date": "2023-06-15",
        "warranty_end": "2024-06-15",
        "warranty_type": "整机1年",
        "status": "已过保",
    },
    "Legion Y9000P": {
        "product": "Legion Y9000P 2024",
        "purchase_date": "2024-03-20",
        "warranty_end": "2027-03-20",
        "warranty_type": "整机1年 + 主要部件延保至3年",
        "status": "在保修期内",
    },
}

# 模拟维修工单数据库
MOCK_REPAIRS = {
    "RPR20240501": {
        "repair_id": "RPR20240501",
        "product": "ThinkPad X1 Carbon Gen 11",
        "issue": "屏幕显示异常，出现彩色条纹",
        "status": "维修中",
        "received_date": "2024-05-01",
        "estimated_completion": "2024-05-16",
        "technician_note": "已确认为屏幕排线故障，配件已到，预计2个工作日完成",
    },
    "RPR20240428": {
        "repair_id": "RPR20240428",
        "product": "Legion Y9000P 2024",
        "issue": "键盘部分按键失灵",
        "status": "待取机",
        "received_date": "2024-04-28",
        "estimated_completion": "2024-05-10",
        "technician_note": "已更换键盘模块，测试正常，请携带取机凭证到店取机",
    },
    "RPR20240505": {
        "repair_id": "RPR20240505",
        "product": "ThinkPad T14s Gen 4",
        "issue": "电池无法充电",
        "status": "已接单，等待检测",
        "received_date": "2024-05-05",
        "estimated_completion": "2024-05-20",
        "technician_note": "设备已收到，排队等待工程师检测",
    },
}


@function_tool
async def query_order_status(order_id: str) -> str:
    """
    查询订单状态和物流信息。

    Args:
        order_id: 订单编号，如 ORD20240512001

    Returns:
        订单状态信息，包含商品名称、物流状态、预计送达时间
    """
    logger.info(f"[AfterSales] 查询订单状态: {order_id}")

    order = MOCK_ORDERS.get(order_id.upper())
    if order:
        return (
            f"订单 {order['order_id']} 状态：\n"
            f"- 商品：{order['product']}\n"
            f"- 状态：{order['status']}\n"
            f"- 物流：{order['logistics']}\n"
            f"- 预计送达：{order['estimated_delivery']}\n"
            f"- 下单日期：{order['purchase_date']}"
        )
    return f"未找到订单号 {order_id}，请确认订单号是否正确。订单号格式通常为 ORD 开头，如 ORD20240512001。"


@function_tool
async def query_warranty_info(product: str) -> str:
    """
    查询产品的保修信息和保修状态。

    Args:
        product: 产品名称或型号，如 ThinkPad X1 Carbon

    Returns:
        保修信息，包含购买日期、保修到期日、保修类型、当前状态
    """
    logger.info(f"[AfterSales] 查询保修信息: {product}")

    # 模糊匹配
    for key, warranty in MOCK_WARRANTY.items():
        if key.lower() in product.lower() or product.lower() in key.lower():
            return (
                f"{warranty['product']} 保修信息：\n"
                f"- 购买日期：{warranty['purchase_date']}\n"
                f"- 保修到期：{warranty['warranty_end']}\n"
                f"- 保修类型：{warranty['warranty_type']}\n"
                f"- 当前状态：{warranty['status']}"
            )
    return f"未找到产品「{product}」的保修信息，请确认产品型号是否正确。常见型号如：ThinkPad X1 Carbon、ThinkPad T14s、Legion Y9000P。"


@function_tool
async def query_repair_progress(repair_id: str) -> str:
    """
    查询维修工单的进度和状态。

    Args:
        repair_id: 维修工单号，如 RPR20240501

    Returns:
        维修进度信息，包含设备型号、故障描述、当前状态、预计完成时间、工程师备注
    """
    logger.info(f"[AfterSales] 查询维修进度: {repair_id}")

    repair = MOCK_REPAIRS.get(repair_id.upper())
    if repair:
        return (
            f"维修工单 {repair['repair_id']} 进度：\n"
            f"- 设备：{repair['product']}\n"
            f"- 故障：{repair['issue']}\n"
            f"- 当前状态：{repair['status']}\n"
            f"- 送修日期：{repair['received_date']}\n"
            f"- 预计完成：{repair['estimated_completion']}\n"
            f"- 工程师备注：{repair['technician_note']}"
        )
    return f"未找到维修工单 {repair_id}，请确认工单号是否正确。工单号格式通常为 RPR 开头，如 RPR20240501。"

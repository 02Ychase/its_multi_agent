from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger
from pymysql.cursors import DictCursor


def _get_conn():
    return DatabasePool.get_connection()


def init_after_sales_tables():
    """创建售后相关的三张表。"""
    conn = _get_conn()
    try:
        cursor = conn.cursor()

        # 订单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(32) UNIQUE NOT NULL COMMENT '订单编号',
                user_id INT NULL COMMENT '关联用户ID',
                product VARCHAR(128) NOT NULL COMMENT '商品名称',
                status VARCHAR(64) NOT NULL COMMENT '订单状态',
                logistics VARCHAR(128) NULL COMMENT '物流信息',
                estimated_delivery VARCHAR(64) NULL COMMENT '预计送达',
                purchase_date DATE NOT NULL COMMENT '下单日期',
                amount DECIMAL(10,2) NULL COMMENT '订单金额',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_order_id (order_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 保修记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warranty_records (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                product VARCHAR(128) NOT NULL COMMENT '产品型号',
                serial_number VARCHAR(64) NULL COMMENT '序列号',
                purchase_date DATE NOT NULL COMMENT '购买日期',
                warranty_end DATE NOT NULL COMMENT '保修到期',
                warranty_type VARCHAR(128) NOT NULL COMMENT '保修类型',
                status VARCHAR(32) NOT NULL COMMENT '保修状态',
                user_id INT NULL COMMENT '关联用户ID',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_product (product),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 维修工单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repair_tickets (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                repair_id VARCHAR(32) UNIQUE NOT NULL COMMENT '工单编号',
                product VARCHAR(128) NOT NULL COMMENT '设备型号',
                issue TEXT NOT NULL COMMENT '故障描述',
                status VARCHAR(64) NOT NULL COMMENT '维修状态',
                received_date DATE NOT NULL COMMENT '送修日期',
                estimated_completion DATE NULL COMMENT '预计完成',
                technician_note TEXT NULL COMMENT '工程师备注',
                user_id INT NULL COMMENT '关联用户ID',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_repair_id (repair_id),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        conn.commit()
        logger.info("After-sales tables initialized (orders, warranty_records, repair_tickets)")
    except Exception as e:
        logger.error(f"Failed to create after-sales tables: {e}")
        raise
    finally:
        conn.close()


def query_order_by_id(order_id: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor(DictCursor)
        cursor.execute(
            "SELECT order_id, product, status, logistics, estimated_delivery, purchase_date, amount "
            "FROM orders WHERE order_id = %s",
            (order_id.upper(),)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def query_warranty_by_product(product: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor(DictCursor)
        cursor.execute(
            "SELECT product, purchase_date, warranty_end, warranty_type, status "
            "FROM warranty_records WHERE product LIKE %s ORDER BY purchase_date DESC LIMIT 1",
            (f"%{product}%",)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def query_repair_by_id(repair_id: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor(DictCursor)
        cursor.execute(
            "SELECT repair_id, product, issue, status, received_date, estimated_completion, technician_note "
            "FROM repair_tickets WHERE repair_id = %s",
            (repair_id.upper(),)
        )
        return cursor.fetchone()
    finally:
        conn.close()

"""端到端（E2E）接口冒烟测试：对**已启动**的后端发真实 HTTP 请求，串起主业务流程。

与 `test_*.py` 里的单元测试不同，本模块不 mock 任何依赖，会真实写入数据库：

    登录 → 主数据（仓库/库位/分类/配件/供应商/车型/车辆/用户）
        → 入库（草稿→待审→已入库，生成二维码库存件）
        → 出库（关联工单领料，扣减库存）
        → 调拨（批量件 + 按件追踪件，调出→调入）
        → 盘点（快照→扫码→录实盘→完成，按差异调整库存）
        → 工单（待修→维修中→完工→结算）
        → 报表（库存/流水/单车成本/看板/导出）与扫码查询
        → 前端 Vite 代理（可选）

运行前置：
    1. 后端已启动（默认 http://127.0.0.1:8080），数据库可用；
    2. 存在管理员账号（默认 admin / admin123）；
    3. 建议只在开发库执行——用例会留下 E2E 前缀的主数据与单据。

运行方式（在 backend 目录）：
    $env:E2E_BASE_URL = "http://127.0.0.1:8080"
    $env:E2E_FRONTEND_URL = "http://127.0.0.1:5173"   # 可选，验证 Vite 代理
    venv\\Scripts\\python.exe -m pytest tests\\test_e2e_live.py -v -s

未设置 `E2E_BASE_URL` 时整个模块自动跳过，普通 `pytest` 仍只跑不依赖数据库的单元测试。

环境变量：
    E2E_BASE_URL      后端地址（必填，未设置则跳过）
    E2E_USERNAME      登录名，默认 admin
    E2E_PASSWORD      登录密码，默认 admin123
    E2E_FRONTEND_URL  前端地址（可选）；设置后额外校验首页与 `/api` 代理

注意：本机若开启了系统代理，httpx 必须 `trust_env=False`，否则发往 127.0.0.1
的请求会被转发到代理并返回 502。
"""

from __future__ import annotations

import os
import time
from decimal import Decimal
from typing import Any

import httpx
import pytest

BASE_URL: str = os.getenv("E2E_BASE_URL", "").rstrip("/")
FRONTEND_URL: str = os.getenv("E2E_FRONTEND_URL", "").rstrip("/")
USERNAME: str = os.getenv("E2E_USERNAME", "admin")
PASSWORD: str = os.getenv("E2E_PASSWORD", "admin123")

pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="未设置 E2E_BASE_URL，跳过真实服务的端到端冒烟测试",
)

# 后端统一前缀（前端经 Vite 代理时是 /api → /api/v1）
API: str = "/api/v1"
# 本次运行的唯一后缀，避免重复执行时编码/车牌/用户名冲突
RUN_ID: str = time.strftime("%m%d%H%M%S")
# 各步骤共享的 ID / 单号（按测试函数定义顺序逐步填充）
STATE: dict[str, Any] = {}


# ---------------------------------------------------------------- 公共工具
def _num(value: Any) -> Decimal:
    """把响应里的数值（float / str / int / None）统一转成 Decimal 便于比较。"""
    return Decimal(str(value if value is not None else 0))


def _detail(response: httpx.Response) -> str:
    """拼装断言失败时的上下文：方法、URL、HTTP 状态与响应片段。"""
    return (
        f"{response.request.method} {response.request.url} "
        f"-> HTTP {response.status_code} | {response.text[:500]}"
    )


def _ok(response: httpx.Response) -> Any:
    """断言 HTTP 200 且业务码 200，返回 `data`。"""
    assert response.status_code == 200, _detail(response)
    body = response.json()
    assert body.get("code") == 200, (
        f"业务失败 | {response.request.method} {response.request.url} | "
        f"code={body.get('code')} message={body.get('message')}"
    )
    return body.get("data")


def _fail(
    response: httpx.Response,
    code: int,
    http_status: int = 200,
    message: str | None = None,
) -> None:
    """断言业务错误码（默认 HTTP 200 + body.code，鉴权错误保留 HTTP 状态码）。

    `message` 传入时额外断言提示文案包含该片段。
    """
    assert response.status_code == http_status, _detail(response)
    body = response.json()
    assert body.get("code") == code, (
        f"错误码不符 | {response.request.method} {response.request.url} | "
        f"期望 code={code}，实际 code={body.get('code')} "
        f"message={body.get('message')}"
    )
    if message is not None:
        assert message in str(body.get("message")), (
            f"错误提示不符 | {response.request.method} {response.request.url} | "
            f"期望包含 {message!r}，实际 message={body.get('message')!r}"
        )


def _login(client: httpx.Client, username: str, password: str) -> str:
    """登录并返回 access token。"""
    data = _ok(
        client.post(
            f"{API}/auth/login",
            json={"username": username, "password": password},
        )
    )
    return str(data["token"])


def _new_client(token: str | None = None) -> httpx.Client:
    """新建客户端；`trust_env=False` 绕过系统代理，保证直连本机服务。"""
    client = httpx.Client(base_url=BASE_URL, timeout=60.0, trust_env=False)
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(scope="module")
def anon() -> Any:
    """未登录客户端（用系统代理会 502，因此关闭 trust_env）。"""
    with httpx.Client(base_url=BASE_URL, timeout=60.0, trust_env=False) as client:
        yield client


@pytest.fixture(scope="module")
def api() -> Any:
    """已登录管理员客户端。"""
    client = _new_client()
    token = _login(client, USERNAME, PASSWORD)
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    client.close()


# ---------------------------------------------------------------- 1. 服务存活
def test_01_health_and_openapi(anon: httpx.Client) -> None:
    """健康检查 + OpenAPI 文档可用，且核心路由已挂载。"""
    data = _ok(anon.get("/health"))
    assert data["status"] == "ok"

    spec = anon.get("/openapi.json")
    assert spec.status_code == 200, _detail(spec)
    paths = set(spec.json()["paths"])
    for expected in (
        f"{API}/auth/login",
        f"{API}/inbound-orders",
        f"{API}/outbound-orders",
        f"{API}/transfer-orders",
        f"{API}/stocktake-orders",
        f"{API}/work-orders",
        f"{API}/reports/dashboard",
        f"{API}/scan/inventory-item",
    ):
        assert expected in paths, f"OpenAPI 缺少路由 {expected}"
    print(f"\n[01] OpenAPI 路由数={len(paths)}")


# ---------------------------------------------------------------- 2. 认证
def test_02_auth(anon: httpx.Client, api: httpx.Client) -> None:
    """错误密码 / 未登录 / 非法 token 被拒；正确登录可访问 /auth/me。"""
    _fail(
        anon.post(
            f"{API}/auth/login",
            json={"username": USERNAME, "password": "e2e-wrong-password"},
        ),
        code=401,
    )
    # 未携带 token：HTTP 401
    _fail(anon.get(f"{API}/auth/me"), code=401, http_status=401)
    # token 非法：HTTP 401
    _fail(
        anon.get(
            f"{API}/auth/me",
            headers={"Authorization": "Bearer not-a-valid-token"},
        ),
        code=401,
        http_status=401,
    )

    me = _ok(api.get(f"{API}/auth/me"))
    assert me["username"] == USERNAME
    assert me["role"] == "admin"
    assert me["realName"]
    print(f"\n[02] 登录成功 user={me['username']} role={me['role']}")


# ---------------------------------------------------------------- 3. 主数据
def test_03_master_data(api: httpx.Client) -> None:
    """仓库/库位/供应商/分类/配件 创建、修改与查询。"""
    # --- 仓库：新建 → 修改 → 关键字查询
    wh = _ok(
        api.post(
            f"{API}/warehouses",
            json={"name": f"E2E中转仓-{RUN_ID}", "address": "E2E 测试地址"},
        )
    )
    STATE["wh2"] = wh["id"]
    wh = _ok(
        api.put(
            f"{API}/warehouses/{wh['id']}",
            json={"address": "E2E 二号地址", "remark": f"E2E {RUN_ID}"},
        )
    )
    assert wh["address"] == "E2E 二号地址"
    page = _ok(api.get(f"{API}/warehouses", params={"keyword": f"E2E中转仓-{RUN_ID}"}))
    assert page["total"] == 1 and page["list"][0]["id"] == STATE["wh2"]
    _fail(api.get(f"{API}/warehouses/99999999"), code=404, message="仓库不存在")

    # --- 库位：主仓（1）与中转仓各建一个，供后续入库/出库/调拨/盘点使用
    loc1 = _ok(
        api.post(
            f"{API}/warehouse-locations",
            json={"warehouse_id": 1, "location_code": f"E2E-A-{RUN_ID}"},
        )
    )
    loc2 = _ok(
        api.post(
            f"{API}/warehouse-locations",
            json={
                "warehouse_id": STATE["wh2"],
                "location_code": f"E2E-B-{RUN_ID}",
                "remark": "E2E 调拨入库位",
            },
        )
    )
    STATE["loc1"], STATE["loc2"] = loc1["id"], loc2["id"]
    assert loc1["warehouseId"] == 1 and loc2["warehouseId"] == STATE["wh2"]
    # 同仓重复库位编码应被拒（409 冲突）
    _fail(
        api.post(
            f"{API}/warehouse-locations",
            json={"warehouse_id": 1, "location_code": f"E2E-A-{RUN_ID}"},
        ),
        code=409,
        message="库位编码已存在",
    )
    page = _ok(
        api.get(
            f"{API}/warehouse-locations",
            params={"warehouseId": STATE["wh2"], "keyword": f"E2E-B-{RUN_ID}"},
        )
    )
    assert page["total"] == 1

    # --- 供应商
    supplier = _ok(
        api.post(
            f"{API}/suppliers",
            json={
                "name": f"E2E配件供应商-{RUN_ID}",
                "contact": "张三",
                "phone": "13800000000",
                "address": "E2E 供应商地址",
                "main_category": "润滑油",
                "payment_term": "月结30天",
            },
        )
    )
    STATE["supplier"] = supplier["id"]
    supplier = _ok(
        api.put(
            f"{API}/suppliers/{supplier['id']}",
            json={"phone": "13900000000", "remark": f"E2E {RUN_ID}"},
        )
    )
    assert supplier["phone"] == "13900000000"

    # --- 配件分类：在已有父分类（1）下建子分类，校验树结构
    category = _ok(
        api.post(
            f"{API}/part-categories",
            json={"name": f"E2E机油-{RUN_ID}", "parent_id": 1, "sort": 99},
        )
    )
    STATE["category"] = category["id"]
    tree = _ok(api.get(f"{API}/part-categories/tree"))
    parent = next(node for node in tree if node["id"] == 1)
    child = next(node for node in parent["children"] if node["id"] == STATE["category"])
    assert child["name"] == f"E2E机油-{RUN_ID}"

    # --- 配件：一个按件追踪（扫码）+ 一个批量管理
    tracked = _ok(
        api.post(
            f"{API}/parts",
            json={
                "part_code": f"E2E{RUN_ID}T",
                "part_name": f"E2E追踪件-{RUN_ID}",
                "category_id": STATE["category"],
                "spec": "4L",
                "brand": "E2E",
                "unit": "个",
                "track_by_item": 1,
                "scan_enabled": 1,
                "safety_stock": 2,
                "max_stock": 50,
            },
        )
    )
    bulk = _ok(
        api.post(
            f"{API}/parts",
            json={
                "part_code": f"E2E{RUN_ID}B",
                "part_name": f"E2E批量件-{RUN_ID}",
                "category_id": STATE["category"],
                "spec": "18L",
                "brand": "E2E",
                "unit": "桶",
                "track_by_item": 0,
                "safety_stock": 10,
                "max_stock": 200,
            },
        )
    )
    STATE["part_tracked"], STATE["part_bulk"] = tracked["id"], bulk["id"]
    assert tracked["trackByItem"] == 1 and tracked["scanEnabled"] == 1
    assert bulk["trackByItem"] == 0
    assert tracked["categoryName"] == f"E2E机油-{RUN_ID}"
    # 配件编码唯一（1001）
    _fail(
        api.post(
            f"{API}/parts",
            json={
                "part_code": f"E2E{RUN_ID}T",
                "part_name": "重复编码",
                "unit": "个",
            },
        ),
        code=1001,
        message="配件编码已存在",
    )
    bulk = _ok(
        api.put(
            f"{API}/parts/{STATE['part_bulk']}",
            json={"safety_stock": 12, "max_stock": 200, "remark": f"E2E {RUN_ID}"},
        )
    )
    assert _num(bulk["safetyStock"]) == 12
    page = _ok(api.get(f"{API}/parts", params={"keyword": f"E2E{RUN_ID}"}))
    assert page["total"] == 2
    detail = _ok(api.get(f"{API}/parts/{STATE['part_tracked']}"))
    assert detail["partCode"] == f"E2E{RUN_ID}T"


def test_03b_master_data_relations(api: httpx.Client) -> None:
    """单位换算、适用车型、车辆、用户等关联主数据。"""
    # --- 单位换算：新增 → 列表 → 删除
    conv = _ok(
        api.post(
            f"{API}/parts/{STATE['part_bulk']}/units",
            json={"from_unit": "桶", "to_unit": "升", "rate": 18},
        )
    )
    assert _num(conv["rate"]) == 18
    units = _ok(api.get(f"{API}/parts/{STATE['part_bulk']}/units"))
    assert len(units) == 1 and units[0]["fromUnit"] == "桶"
    _ok(api.delete(f"{API}/parts/{STATE['part_bulk']}/units/{conv['id']}"))
    assert _ok(api.get(f"{API}/parts/{STATE['part_bulk']}/units")) == []

    # --- 车型 + 适用车型映射
    model = _ok(
        api.post(
            f"{API}/vehicle-models",
            json={"brand": "E2E解放", "model_name": f"J6-{RUN_ID}", "tonnage": "10吨"},
        )
    )
    STATE["model"] = model["id"]
    _ok(
        api.post(
            f"{API}/parts/{STATE['part_tracked']}/models",
            json={"model_id": STATE["model"], "remark": "E2E 适配"},
        )
    )
    page = _ok(api.get(f"{API}/parts/{STATE['part_tracked']}/models"))
    assert len(page) == 1
    assert page[0]["modelName"] == f"J6-{RUN_ID}"

    # --- 车辆
    vehicle = _ok(
        api.post(
            f"{API}/vehicles",
            json={
                "plate_no": f"京A{RUN_ID}E",
                "model_id": STATE["model"],
                "vin": f"LVIN{RUN_ID}0001",
                "department": "E2E车队",
                "mileage": 1000,
            },
        )
    )
    STATE["vehicle"] = vehicle["id"]
    STATE["plate"] = vehicle["plateNo"]
    assert vehicle["modelName"] == f"J6-{RUN_ID}"
    vehicle = _ok(
        api.put(
            f"{API}/vehicles/{vehicle['id']}",
            json={"mileage": 1500, "department": "E2E车队A"},
        )
    )
    assert vehicle["mileage"] == 1500
    page = _ok(api.get(f"{API}/vehicles", params={"keyword": STATE["plate"]}))
    assert page["total"] == 1

    # --- 用户：库管 + 只读（供下一节角色权限校验）
    keeper = _ok(
        api.post(
            f"{API}/users",
            json={
                "username": f"e2e_keeper_{RUN_ID}",
                "password": "e2e123456",
                "real_name": "E2E 库管",
                "role": "keeper",
                "default_warehouse_id": 1,
            },
        )
    )
    readonly = _ok(
        api.post(
            f"{API}/users",
            json={
                "username": f"e2e_readonly_{RUN_ID}",
                "password": "e2e123456",
                "real_name": "E2E 只读",
                "role": "readonly",
            },
        )
    )
    STATE["keeper_id"], STATE["readonly_id"] = keeper["id"], readonly["id"]
    STATE["keeper_user"] = keeper["username"]
    STATE["readonly_user"] = readonly["username"]
    assert keeper["role"] == "keeper" and keeper["defaultWarehouseId"] == 1
    page = _ok(api.get(f"{API}/users", params={"keyword": STATE["keeper_user"]}))
    assert page["total"] == 1
    print(
        f"\n[03] 主数据就绪 wh2={STATE['wh2']} loc1={STATE['loc1']} "
        f"loc2={STATE['loc2']} part_tracked={STATE['part_tracked']} "
        f"part_bulk={STATE['part_bulk']} vehicle={STATE['vehicle']}"
    )


# ---------------------------------------------------------------- 4. 权限
def test_04_role_permission(api: httpx.Client) -> None:
    """只读账号只能查询；库管账号可写入；停用后 token 立即失效。"""
    with _new_client() as client:
        token = _login(client, STATE["readonly_user"], "e2e123456")
        client.headers["Authorization"] = f"Bearer {token}"
        assert _ok(client.get(f"{API}/auth/me"))["role"] == "readonly"
        # 只读可查询
        assert _ok(client.get(f"{API}/parts"))["total"] >= 1
        # 写操作被拒：HTTP 403
        _fail(
            client.post(
                f"{API}/parts",
                json={
                    "part_code": f"E2E{RUN_ID}X",
                    "part_name": "越权写入",
                    "unit": "个",
                },
            ),
            code=403,
            http_status=403,
        )
        _fail(api.post(f"{API}/inbound-orders", json={"items": []}), code=400)

        # 停用只读账号后，已签发的 token 立即失效
        _ok(api.put(f"{API}/users/{STATE['readonly_id']}/status", json={"status": 0}))
        try:
            _fail(client.get(f"{API}/auth/me"), code=401, http_status=401)
            _fail(
                client.post(
                    f"{API}/auth/login",
                    json={
                        "username": STATE["readonly_user"],
                        "password": "e2e123456",
                    },
                ),
                code=403,
            )
        finally:
            _ok(
                api.put(
                    f"{API}/users/{STATE['readonly_id']}/status", json={"status": 1}
                )
            )

        # 重置密码：旧密码失效、新密码可登录
        _ok(
            api.put(
                f"{API}/users/{STATE['readonly_id']}/password",
                json={"password": "e2e654321"},
            )
        )
        _fail(
            client.post(
                f"{API}/auth/login",
                json={"username": STATE["readonly_user"], "password": "e2e123456"},
            ),
            code=401,
        )
        assert _login(client, STATE["readonly_user"], "e2e654321")

    # 库管账号可读入库单
    with _new_client() as keeper_client:
        token = _login(keeper_client, STATE["keeper_user"], "e2e123456")
        keeper_client.headers["Authorization"] = f"Bearer {token}"
        assert _ok(keeper_client.get(f"{API}/auth/me"))["role"] == "keeper"
        assert _ok(keeper_client.get(f"{API}/inbound-orders"))["total"] >= 0

    print("\n[04] 角色权限通过：readonly 写操作 403，停用账号 token 失效")


# ---------------------------------------------------------------- 5. 入库
def test_05_inbound_flow(api: httpx.Client) -> None:
    """入库单：草稿→提交→审核，审核后生成库存件并增加库存；重复审核被拒。"""
    order = _ok(
        api.post(
            f"{API}/inbound-orders",
            json={
                "supplier_id": STATE["supplier"],
                "warehouse_id": 1,
                "inbound_type": "PURCHASE",
                "remark": f"E2E 入库 {RUN_ID}",
                "items": [
                    {
                        "part_id": STATE["part_tracked"],
                        "quantity": "3",
                        "unit_price": "12.5000",
                        "location_id": STATE["loc1"],
                        "batch_no": f"B{RUN_ID}T",
                    },
                    {
                        "part_id": STATE["part_bulk"],
                        "quantity": "10",
                        "unit_price": "5.0000",
                        "location_id": STATE["loc1"],
                        "batch_no": f"B{RUN_ID}B",
                    },
                ],
            },
        )
    )
    STATE["inbound"] = order["id"]
    STATE["inbound_no"] = order["orderNo"]
    assert order["status"] == 1, "新建入库单应为草稿（1）"
    assert order["orderNo"].startswith("IN")
    assert _num(order["totalAmount"]) == Decimal("87.50")
    assert len(order["items"]) == 2

    # 草稿可修改
    order = _ok(
        api.put(
            f"{API}/inbound-orders/{order['id']}",
            json={"remark": f"E2E 入库-编辑 {RUN_ID}"},
        )
    )
    assert order["remark"] == f"E2E 入库-编辑 {RUN_ID}"

    order = _ok(api.post(f"{API}/inbound-orders/{order['id']}/submit"))
    assert order["status"] == 2, "提交后应为待审核（2）"

    order = _ok(api.post(f"{API}/inbound-orders/{order['id']}/approve"))
    assert order["status"] == 3, "审核后应为已入库（3）"
    assert order["inboundAt"]
    tracked_line = next(
        item for item in order["items"] if item["partId"] == STATE["part_tracked"]
    )
    assert tracked_line["trackByItem"] == 1
    assert tracked_line["generated"] == 1
    assert _num(tracked_line["generateItemQty"]) == 3

    # 重复审核：单据状态不允许（3001）
    _fail(api.post(f"{API}/inbound-orders/{order['id']}/approve"), code=3001)
    # 已入库单据不可修改
    _fail(
        api.put(f"{API}/inbound-orders/{order['id']}", json={"remark": "非法修改"}),
        code=3001,
    )

    page = _ok(api.get(f"{API}/inbound-orders", params={"keyword": order["orderNo"]}))
    assert page["total"] == 1 and page["list"][0]["status"] == 3

    # 草稿作废 → 4
    draft = _ok(
        api.post(
            f"{API}/inbound-orders",
            json={
                "warehouse_id": 1,
                "inbound_type": "ADJUST",
                "remark": "E2E 待作废草稿",
                "items": [
                    {
                        "part_id": STATE["part_bulk"],
                        "quantity": "1",
                        "unit_price": "5.0000",
                        "location_id": STATE["loc1"],
                    }
                ],
            },
        )
    )
    draft = _ok(api.post(f"{API}/inbound-orders/{draft['id']}/cancel"))
    assert draft["status"] == 4
    print(f"\n[05] 入库完成 {order['orderNo']} 金额={order['totalAmount']}")
    print(f"[05] 待入库草稿作废 {draft['orderNo']} -> 状态 {draft['status']}")


# ---------------------------------------------------------------- 6. 库存与扫码
def test_06_inventory_and_scan(api: httpx.Client) -> None:
    """入库后库存汇总、库存件生成、二维码扫描与流水记录。"""
    page = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_tracked"], "warehouseId": 1},
        )
    )
    row = page["list"][0]
    assert _num(row["quantity"]) == 3
    assert row["itemCount"] == 3
    assert _num(row["avgCost"]) == Decimal("12.5")
    assert _num(row["lockedQty"]) == 0

    page = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_bulk"], "warehouseId": 1},
        )
    )
    row = page["list"][0]
    assert _num(row["quantity"]) == 10
    assert row["itemCount"] == 0, "批量管理配件不生成库存件"
    assert _num(row["avgCost"]) == Decimal(5)

    items = _ok(
        api.get(
            f"{API}/inventory-items",
            params={"partId": STATE["part_tracked"], "status": 1},
        )
    )
    assert items["total"] == 3
    codes = [entry["itemCode"] for entry in items["list"]]
    assert len(set(codes)) == 3, "库存件编码应唯一"
    STATE["items"] = [entry["id"] for entry in items["list"]]
    first = items["list"][0]
    assert first["status"] == 1
    assert first["qrcode"]
    assert _num(first["unitCost"]) == Decimal("12.5")

    detail = _ok(api.get(f"{API}/inventory-items/{first['id']}"))
    assert detail["partCode"] == f"E2E{RUN_ID}T"
    assert detail["statusText"] == "在库"
    assert detail["warehouseId"] == 1 and detail["locationId"] == STATE["loc1"]

    # 扫码：原始编码 / 带 QR: 前缀与空白的容错
    scan = _ok(api.get(f"{API}/scan/inventory-item", params={"code": first["qrcode"]}))
    assert scan["itemId"] == first["id"]
    assert scan["partId"] == STATE["part_tracked"]
    assert scan["status"] == 1
    scan = _ok(
        api.get(
            f"{API}/scan/inventory-item",
            params={"code": f"  QR:{first['qrcode']}  "},
        )
    )
    assert scan["itemId"] == first["id"]
    # 无法识别的编码：4001
    _fail(
        api.get(f"{API}/scan/inventory-item", params={"code": "E2E-NOT-EXIST"}),
        code=4001,
    )

    # 入库流水（按配件维度写入，库存件实例通过 inbound_item_id 关联）
    tx = _ok(
        api.get(
            f"{API}/reports/transaction",
            params={
                "partId": STATE["part_tracked"],
                "bizType": "IN",
                "refNo": STATE["inbound_no"],
            },
        )
    )
    assert tx["total"] == 1, "应恰好有一条本单入库流水"
    assert tx["list"][0]["refType"] == "INBOUND"
    assert _num(tx["list"][0]["changeQty"]) == 3
    assert _num(tx["summary"]["inQty"]) == 3

    STATE["item_out"] = first["id"]
    STATE["item_code_out"] = first["itemCode"]
    print(f"\n[06] 库存校验通过 tracked=3 items=3 bulk=10 扫码={first['itemCode']}")


# ---------------------------------------------------------------- 7. 维修工单
def test_07_work_order_start(api: httpx.Client) -> None:
    """工单：新建（待修）→ 开始维修（维修中）。"""
    wo = _ok(
        api.post(
            f"{API}/work-orders",
            json={
                "vehicle_id": STATE["vehicle"],
                "repair_type": "REPAIR",
                "description": f"E2E 更换机油 {RUN_ID}",
                "repair_man_id": 1,
            },
        )
    )
    STATE["work_order"] = wo["id"]
    assert wo["status"] == 1, "新建工单应为待修（1）"
    assert wo["orderNo"].startswith("WO")
    assert wo["plateNo"] == STATE["plate"]

    wo = _ok(api.post(f"{API}/work-orders/{wo['id']}/start"))
    assert wo["status"] == 2, "开始维修后应为维修中（2）"
    assert wo["inAt"]

    page = _ok(
        api.get(
            f"{API}/work-orders",
            params={"status": 2, "vehicleId": STATE["vehicle"]},
        )
    )
    assert page["total"] >= 1
    assert any(row["id"] == STATE["work_order"] for row in page["list"])
    print(f"\n[07] 工单 {wo['orderNo']} 进入维修中")


# ---------------------------------------------------------------- 8. 出库
def test_08_outbound_flow(api: httpx.Client) -> None:
    """出库单：扫码件 + 批量件 → 审核出库，扣减库存、联动工单领料。"""
    order = _ok(
        api.post(
            f"{API}/outbound-orders",
            json={
                "warehouse_id": 1,
                "outbound_type": "REPAIR",
                "vehicle_id": STATE["vehicle"],
                "work_order_id": STATE["work_order"],
                "receiver_id": 1,
                "remark": f"E2E 领料 {RUN_ID}",
                "items": [
                    {
                        "part_id": STATE["part_tracked"],
                        "inventory_item_id": STATE["item_out"],
                        "quantity": "1",
                        "unit_cost": "12.5000",
                        "scan_code": STATE["item_code_out"],
                        "scan_type": "QRCODE",
                    },
                    {
                        "part_id": STATE["part_bulk"],
                        "quantity": "2",
                        "unit_cost": "5.0000",
                        "location_id": STATE["loc1"],
                    },
                ],
            },
        )
    )
    STATE["outbound"] = order["id"]
    assert order["status"] == 1
    assert order["orderNo"].startswith("OUT")
    assert _num(order["totalAmount"]) == Decimal("22.50")
    scanned = next(item for item in order["items"] if item["inventoryItemId"])
    assert scanned["scanType"] == "QRCODE"
    assert scanned["itemCode"] == STATE["item_code_out"]

    order = _ok(api.post(f"{API}/outbound-orders/{order['id']}/submit"))
    assert order["status"] == 2
    order = _ok(api.post(f"{API}/outbound-orders/{order['id']}/approve"))
    assert order["status"] == 3
    assert order["outboundAt"]
    assert order["vehiclePlateNo"] == STATE["plate"]

    # 库存件变为已出库，并记录工单 / 车辆
    item = _ok(api.get(f"{API}/inventory-items/{STATE['item_out']}"))
    assert item["status"] == 3 and item["statusText"] == "已出库"
    assert item["workOrderId"] == STATE["work_order"]
    assert item["vehicleId"] == STATE["vehicle"]
    # 已出库件再次出库 → 2003
    _fail(
        api.get(f"{API}/scan/inventory-item", params={"code": STATE["item_code_out"]}),
        code=2003,
    )

    # 库存扣减：tracked 3→2（件数 3→2），bulk 10→8
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_tracked"], "warehouseId": 1},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 2 and row["itemCount"] == 2
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_bulk"], "warehouseId": 1},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 8

    # 出库流水写入库存件维度（扫码件一条 OUT 流水）
    tx = _ok(api.get(f"{API}/inventory-items/{STATE['item_out']}/transactions"))
    assert tx["total"] == 1
    assert tx["list"][0]["bizType"] == "OUT"
    assert _num(tx["list"][0]["changeQty"]) == -1
    assert tx["list"][0]["refNo"].startswith("OUT")


def test_08b_outbound_insufficient_stock(api: httpx.Client) -> None:
    """库存不足时审核失败（2001），单据可作废；草稿领料校验。"""
    order = _ok(
        api.post(
            f"{API}/outbound-orders",
            json={
                "warehouse_id": 1,
                "outbound_type": "REPAIR",
                "remark": "E2E 库存不足用例",
                "items": [
                    {
                        "part_id": STATE["part_bulk"],
                        "quantity": "999",
                        "unit_cost": "5.0000",
                        "location_id": STATE["loc1"],
                    }
                ],
            },
        )
    )
    _ok(api.post(f"{API}/outbound-orders/{order['id']}/submit"))
    _fail(api.post(f"{API}/outbound-orders/{order['id']}/approve"), code=2001)
    order = _ok(api.post(f"{API}/outbound-orders/{order['id']}/cancel"))
    assert order["status"] == 4

    # 非法出库类型：400
    _fail(
        api.post(
            f"{API}/outbound-orders",
            json={"warehouse_id": 1, "outbound_type": "NOT_EXIST", "items": []},
        ),
        code=400,
    )
    # 空明细单据可存草稿，但提交时报 400
    empty = _ok(
        api.post(
            f"{API}/outbound-orders",
            json={"warehouse_id": 1, "outbound_type": "REPAIR", "items": []},
        )
    )
    assert empty["items"] == []
    _fail(
        api.post(f"{API}/outbound-orders/{empty['id']}/submit"),
        code=400,
        message="明细不能为空",
    )
    assert _ok(api.post(f"{API}/outbound-orders/{empty['id']}/cancel"))["status"] == 4
    # 已出库单据不可作废
    _fail(api.post(f"{API}/outbound-orders/{STATE['outbound']}/cancel"), code=3001)
    print(f"\n[08] 出库完成 {STATE['outbound']} 库存扣减/工单领料校验通过")


# ---------------------------------------------------------------- 9. 调拨
def test_09_transfer_flow(api: httpx.Client) -> None:
    """调拨：批量件调出→调入；按件追踪件调拨时锁定实例并迁移仓库/库位。"""
    # 同仓调拨被拒
    _fail(
        api.post(
            f"{API}/transfer-orders",
            json={"from_warehouse_id": 1, "to_warehouse_id": 1, "items": []},
        ),
        code=400,
    )

    order = _ok(
        api.post(
            f"{API}/transfer-orders",
            json={
                "from_warehouse_id": 1,
                "to_warehouse_id": STATE["wh2"],
                "remark": f"E2E 批量件调拨 {RUN_ID}",
                "items": [
                    {
                        "part_id": STATE["part_bulk"],
                        "quantity": "4",
                        "from_location_id": STATE["loc1"],
                        "to_location_id": STATE["loc2"],
                    }
                ],
            },
        )
    )
    STATE["transfer_bulk"] = order["id"]
    assert order["status"] == 1
    assert order["fromWarehouseName"] and order["toWarehouseName"]

    order = _ok(api.post(f"{API}/transfer-orders/{order['id']}/transfer-out"))
    assert order["status"] == 3, "确认调出后应为已调出（3）"
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_bulk"], "warehouseId": 1},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 4

    order = _ok(api.post(f"{API}/transfer-orders/{order['id']}/transfer-in"))
    assert order["status"] == 4, "确认调入后应为已调入（4）"
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_bulk"], "warehouseId": STATE["wh2"]},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 4
    assert _num(row["avgCost"]) == Decimal(5), "调拨按原成本结转"
    assert row["locationId"] == STATE["loc2"]

    # 已完成单据不可再操作
    _fail(api.post(f"{API}/transfer-orders/{order['id']}/transfer-out"), code=3001)
    _fail(api.post(f"{API}/transfer-orders/{order['id']}/cancel"), code=3001)

    # --- 按件追踪件调拨：调出锁定 → 调入迁移仓库/库位
    remaining = [item_id for item_id in STATE["items"] if item_id != STATE["item_out"]]
    assert len(remaining) == 2
    STATE["item_move"] = remaining[0]
    item = _ok(api.get(f"{API}/inventory-items/{STATE['item_move']}"))
    assert item["status"] == 1

    order = _ok(
        api.post(
            f"{API}/transfer-orders",
            json={
                "from_warehouse_id": 1,
                "to_warehouse_id": STATE["wh2"],
                "remark": f"E2E 追踪件调拨 {RUN_ID}",
                "items": [
                    {
                        "part_id": STATE["part_tracked"],
                        "inventory_item_id": STATE["item_move"],
                        "quantity": "1",
                        "from_location_id": STATE["loc1"],
                        "to_location_id": STATE["loc2"],
                    }
                ],
            },
        )
    )
    STATE["transfer_tracked"] = order["id"]
    order = _ok(api.post(f"{API}/transfer-orders/{order['id']}/transfer-out"))
    assert order["status"] == 3
    item = _ok(api.get(f"{API}/inventory-items/{STATE['item_move']}"))
    assert item["status"] == 2 and item["statusText"] == "锁定"
    # 锁定件不能出库、不能扫码出库
    _fail(
        api.get(f"{API}/scan/inventory-item", params={"code": item["qrcode"]}),
        code=2004,
    )

    order = _ok(api.post(f"{API}/transfer-orders/{order['id']}/transfer-in"))
    assert order["status"] == 4
    item = _ok(api.get(f"{API}/inventory-items/{STATE['item_move']}"))
    assert item["status"] == 1
    assert item["warehouseId"] == STATE["wh2"]
    assert item["locationId"] == STATE["loc2"]

    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_tracked"], "warehouseId": 1},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 1 and row["itemCount"] == 1
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_tracked"], "warehouseId": STATE["wh2"]},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 1 and row["itemCount"] == 1
    print(f"\n[09] 调拨完成 批量件 4 桶、追踪件 {item['itemCode']} 已迁至中转仓")


# ---------------------------------------------------------------- 10. 盘点
def test_10_stocktake_flow(api: httpx.Client) -> None:
    """盘点：快照 → 开始 → 扫码/录实盘 → 完成（按差异调整库存）。

    盘点仓库选用本 run 新建的中转仓，保证快照里只有本次产生的库存，
    不受历史数据干扰。
    """
    order = _ok(
        api.post(
            f"{API}/stocktake-orders",
            json={"warehouse_id": STATE["wh2"], "remark": f"E2E 盘点 {RUN_ID}"},
        )
    )
    STATE["stocktake"] = order["id"]
    assert order["status"] == 1
    assert order["warehouseName"] == f"E2E中转仓-{RUN_ID}"
    rows = order["items"]
    assert len(rows) == 2, "未传明细时应按仓库现有库存自动生成快照"

    bulk_row = next(row for row in rows if row["partId"] == STATE["part_bulk"])
    tracked_row = next(row for row in rows if row["inventoryItemId"])
    assert _num(bulk_row["bookQty"]) == 4, "批量件账面数量应为 4"
    assert _num(bulk_row["actualQty"]) == 4 and _num(bulk_row["diffQty"]) == 0
    # 按件追踪的库存件需扫码确认，快照实盘默认 0（差异 -1）
    assert tracked_row["partId"] == STATE["part_tracked"]
    assert _num(tracked_row["bookQty"]) == 1
    assert _num(tracked_row["actualQty"]) == 0
    assert _num(tracked_row["diffQty"]) == -1
    assert tracked_row["locationCode"] == f"E2E-B-{RUN_ID}"

    # 草稿状态不允许扫码 / 录实盘
    _fail(
        api.put(
            f"{API}/stocktake-orders/{order['id']}/items/{bulk_row['id']}",
            json={"actual_qty": "3"},
        ),
        code=3001,
    )

    order = _ok(api.post(f"{API}/stocktake-orders/{order['id']}/start"))
    assert order["status"] == 2, "开始盘点后应为盘点中（2）"

    # 扫码盘点：命中明细 → 标记已盘
    scanned = _ok(
        api.post(
            f"{API}/stocktake-orders/{order['id']}/scan",
            json={"code": tracked_row["itemCode"], "location_id": STATE["loc2"]},
        )
    )
    assert scanned["id"] == tracked_row["id"]
    assert scanned["scanCode"] == tracked_row["itemCode"]
    assert _num(scanned["actualQty"]) == 1
    # 重复扫码：409
    _fail(
        api.post(
            f"{API}/stocktake-orders/{order['id']}/scan",
            json={"code": tracked_row["itemCode"]},
        ),
        code=409,
    )
    # 无法识别的编码：4001
    _fail(
        api.post(
            f"{API}/stocktake-orders/{order['id']}/scan",
            json={"code": "E2E-NOT-EXIST-CODE"},
        ),
        code=4001,
    )

    # 手工录入实盘：4 → 3（盘亏 1）
    updated = _ok(
        api.put(
            f"{API}/stocktake-orders/{order['id']}/items/{bulk_row['id']}",
            json={"actual_qty": "3", "remark": "E2E 盘亏 1 桶"},
        )
    )
    assert _num(updated["actualQty"]) == 3
    assert _num(updated["diffQty"]) == -1

    order = _ok(api.post(f"{API}/stocktake-orders/{order['id']}/finish"))
    assert order["status"] == 3, "完成后应为已完成（3）"

    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_bulk"], "warehouseId": STATE["wh2"]},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 3, "盘亏后账面数量应下调为 3"
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_tracked"], "warehouseId": STATE["wh2"]},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 1 and row["itemCount"] == 1
    # 主仓库存未受中转仓盘点影响
    row = _ok(
        api.get(
            f"{API}/inventory",
            params={"partId": STATE["part_bulk"], "warehouseId": 1},
        )
    )["list"][0]
    assert _num(row["quantity"]) == 4

    # 已完成单据不可再操作
    _fail(api.post(f"{API}/stocktake-orders/{order['id']}/start"), code=3001)
    _fail(
        api.put(
            f"{API}/stocktake-orders/{order['id']}/items/{bulk_row['id']}",
            json={"actual_qty": "1"},
        ),
        code=3001,
    )

    # 草稿盘点单可作废
    draft = _ok(
        api.post(f"{API}/stocktake-orders", json={"warehouse_id": STATE["wh2"]})
    )
    draft = _ok(api.post(f"{API}/stocktake-orders/{draft['id']}/cancel"))
    assert draft["status"] == 4
    print(f"\n[10] 盘点完成 {order['orderNo']}，盘亏 1 桶已调整库存")


# ---------------------------------------------------------------- 11. 工单完工结算
def test_11_work_order_finish_settle(api: httpx.Client) -> None:
    """工单：完工汇总配件成本 → 结算填写工时费；状态流转非法时报 3001。"""
    wo = _ok(api.post(f"{API}/work-orders/{STATE['work_order']}/finish"))
    assert wo["status"] == 3, "完工后应为已完工（3）"
    assert wo["outAt"]
    assert _num(wo["totalPartsCost"]) == Decimal("22.50"), "配件成本来自出库明细"

    wo = _ok(
        api.post(
            f"{API}/work-orders/{STATE['work_order']}/settle",
            json={"total_labor_cost": "120.50", "remark": f"E2E 结算 {RUN_ID}"},
        )
    )
    assert wo["status"] == 4, "结算后应为已结算（4）"
    assert _num(wo["totalLaborCost"]) == Decimal("120.50")
    _fail(
        api.post(
            f"{API}/work-orders/{STATE['work_order']}/settle",
            json={"total_labor_cost": "1"},
        ),
        code=3001,
    )

    parts = _ok(api.get(f"{API}/work-orders/{STATE['work_order']}/parts"))
    assert len(parts) == 2, "两次领料应生成两条工单领料记录"
    total = sum((_num(row["cost"]) for row in parts), Decimal(0))
    assert total == Decimal("22.50")
    codes = {row["partCode"] for row in parts}
    assert codes == {f"E2E{RUN_ID}T", f"E2E{RUN_ID}B"}
    print(
        f"\n[11] 工单结算完成 配件成本={wo['totalPartsCost']} 工时费={wo['totalLaborCost']}"
    )


# ---------------------------------------------------------------- 12. 报表
def test_12_reports(api: httpx.Client) -> None:
    """库存报表（含低库存/导出）、流水报表、单车成本、首页看板。"""
    # --- 库存报表：按本次运行关键字限定范围，避免受库内其他数据影响
    data = _ok(
        api.get(
            f"{API}/reports/inventory",
            params={"keyword": f"E2E{RUN_ID}", "warehouseId": 1},
        )
    )
    assert data["total"] == 2
    assert data["summary"]["partKinds"] == 2
    assert _num(data["summary"]["totalQuantity"]) == 5  # 追踪件 1 + 批量件 4
    assert _num(data["summary"]["totalAmount"]) == Decimal("32.50")
    assert data["summary"]["lowStockCount"] == 2, "两个配件在仓库 1 均低于安全库存"
    row = next(entry for entry in data["list"] if entry["partId"] == STATE["part_bulk"])
    assert _num(row["quantity"]) == 4 and _num(row["safetyStock"]) == 12
    assert row["warehouseName"] and row["locationCode"] == f"E2E-A-{RUN_ID}"

    # 低库存汇总（两个仓库各一条批量件记录，均低于安全库存）
    data = _ok(
        api.get(
            f"{API}/reports/inventory",
            params={"keyword": f"E2E{RUN_ID}", "lowStock": "true"},
        )
    )
    assert data["total"] == 4 and data["summary"]["lowStockCount"] == 4

    # 低库存预警接口（库存页预警用）：批量件两个仓库都缺货
    data = _ok(
        api.get(
            f"{API}/inventory/warning",
            params={"partId": STATE["part_bulk"]},
        )
    )
    assert data["total"] == 2
    assert all(
        _num(entry["quantity"]) < _num(entry["safetyStock"]) for entry in data["list"]
    )

    # 导出 Excel：返回二进制且 Content-Type 为 xlsx
    export = api.get(
        f"{API}/reports/inventory/export",
        params={"keyword": f"E2E{RUN_ID}"},
    )
    assert export.status_code == 200, _detail(export)
    assert "spreadsheet" in export.headers["content-type"]
    assert "attachment" in export.headers.get("content-disposition", "")
    assert export.content[:2] == b"PK", "xlsx 应为 zip 容器"
    assert len(export.content) > 1000

    # --- 流水报表：入库 +10、出库 -2、调拨 ±4、盘亏 -1
    data = _ok(
        api.get(f"{API}/reports/transaction", params={"partId": STATE["part_bulk"]})
    )
    assert data["total"] == 5
    biz_types = {entry["bizType"] for entry in data["list"]}
    assert biz_types == {
        "IN",
        "OUT",
        "TRANSFER_OUT",
        "TRANSFER_IN",
        "ADJUST_OUT",
    }
    summary = data["summary"]
    assert _num(summary["inQty"]) == 10
    assert _num(summary["outQty"]) == 2
    assert _num(summary["transferInQty"]) == 4
    assert _num(summary["transferOutQty"]) == 4
    assert _num(summary["adjustOutQty"]) == 1
    assert _num(summary["netQty"]) == 7  # 10 - 2 - 4 + 4 - 1

    adjust = _ok(
        api.get(
            f"{API}/reports/transaction",
            params={"partId": STATE["part_bulk"], "bizType": "ADJUST_OUT"},
        )
    )
    assert adjust["total"] == 1
    assert _num(adjust["list"][0]["changeQty"]) == -1
    assert adjust["list"][0]["refType"] == "STOCKTAKE"

    # --- 单车成本：1 次维修，配件 22.50 + 工时 120.50
    cost = _ok(
        api.get(f"{API}/reports/vehicle-cost", params={"vehicleId": STATE["vehicle"]})
    )
    assert cost["total"] == 1
    row = cost["list"][0]
    assert row["plateNo"] == STATE["plate"]
    assert row["repairCount"] == 1
    assert _num(row["totalPartsCost"]) == Decimal("22.50")
    assert _num(row["totalLaborCost"]) == Decimal("120.50")
    assert _num(row["totalCost"]) == Decimal("143.00")
    assert cost["summary"]["vehicleCount"] == 1
    assert _num(cost["summary"]["totalCost"]) == Decimal("143.00")

    # --- 首页看板
    dashboard = _ok(api.get(f"{API}/reports/dashboard"))
    assert dashboard["partCount"] >= 2
    assert dashboard["vehicleCount"] >= 1
    assert dashboard["warehouseCount"] >= 2
    assert _num(dashboard["inventoryQuantity"]) >= 9
    assert _num(dashboard["inventoryAmount"]) >= Decimal(60)
    assert dashboard["lowStockCount"] >= 2
    assert _num(dashboard["monthInboundAmount"]) >= Decimal("87.50")
    assert _num(dashboard["monthOutboundAmount"]) >= Decimal("22.50")
    print(
        f"\n[12] 报表通过 单车成本={cost['summary']['totalCost']} "
        f"看板库存数量={dashboard['inventoryQuantity']} "
        f"看板库存金额={dashboard['inventoryAmount']}"
    )


# ---------------------------------------------------------------- 13. 前端代理
@pytest.mark.skipif(not FRONTEND_URL, reason="未设置 E2E_FRONTEND_URL，跳过前端校验")
def test_13_frontend_proxy() -> None:
    """前端首页可访问，SPA 路由可直达，`/api` 代理能登录并取到业务数据。"""
    with httpx.Client(base_url=FRONTEND_URL, timeout=60.0, trust_env=False) as client:
        # 1) 首页 HTML
        index = client.get("/")
        assert index.status_code == 200, _detail(index)
        assert "text/html" in index.headers["content-type"]
        assert '<div id="app">' in index.text

        # 2) 前端登录（Vite 会把 /api/** 重写为 /api/v1/**）
        data = _ok(
            client.post(
                "/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD},
            )
        )
        client.headers["Authorization"] = f"Bearer {data['token']}"
        dashboard = _ok(client.get("/api/reports/dashboard"))
        assert dashboard["partCount"] >= 2
        page = _ok(client.get("/api/inventory", params={"warehouseId": 1}))
        assert page["total"] >= 1

        # 3) SPA 直达路由返回 index.html（history 模式回退）
        for path in (
            "/login",
            "/dashboard",
            "/part",
            "/vehicle",
            "/supplier",
            "/warehouse",
            "/inventory",
            "/inbound",
            "/outbound",
            "/transfer",
            "/stocktake",
            "/workOrder",
            "/report/inventory",
            "/report/transaction",
            "/report/vehicle-cost",
            "/system/user",
        ):
            resp = client.get(path)
            assert resp.status_code == 200, _detail(resp)
            assert '<div id="app">' in resp.text
    print(f"\n[13] 前端 {FRONTEND_URL} 首页/SPA 路由/Vite 代理均正常")


# ---------------------------------------------------------------- 14. 汇总
def test_14_summary() -> None:
    """汇总本次运行创建的数据，便于在开发库中定位与清理。"""
    print("\n" + "=" * 72)
    print(f"E2E 冒烟完成，运行标识 RUN_ID={RUN_ID}")
    print(f"  后端：{BASE_URL}    前端：{FRONTEND_URL or '未校验'}")
    print(
        f"  主数据：仓库={STATE.get('wh2')} 库位={STATE.get('loc1')}/"
        f"{STATE.get('loc2')} 供应商={STATE.get('supplier')} "
        f"配件={STATE.get('part_tracked')}/{STATE.get('part_bulk')}"
    )
    print(
        f"  车辆={STATE.get('vehicle')} 车牌={STATE.get('plate')} "
        f"车型={STATE.get('model')}"
    )
    print(
        f"  单据：入库={STATE.get('inbound')} 出库={STATE.get('outbound')} "
        f"调拨={STATE.get('transfer_bulk')}/{STATE.get('transfer_tracked')} "
        f"盘点={STATE.get('stocktake')} 工单={STATE.get('work_order')}"
    )
    print(f"  账号：{STATE.get('keeper_user')} / {STATE.get('readonly_user')}")
    print("=" * 72)
    assert STATE.get("work_order") and STATE.get("stocktake")

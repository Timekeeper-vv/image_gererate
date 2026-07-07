from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.pricing.catalog import CATEGORY_INFOS
from app.pricing.engine import quote_product
from app.schemas import CategoryInfo, LeadQuoteRequest, ProductSpec, QuoteResult

app = FastAPI(
    title="之间味道 · 采购生产报价 API",
    description="按品类测算文创产品成本、工期、风险和数量阶梯报价的 MVP 服务。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "pricing-api", "version": "0.1.0"}


@app.get("/categories", response_model=list[CategoryInfo])
def categories() -> list[CategoryInfo]:
    return CATEGORY_INFOS


@app.post("/quote", response_model=QuoteResult)
def quote(spec: ProductSpec) -> QuoteResult:
    return quote_product(spec)


@app.post("/lead-quote", response_model=QuoteResult)
def lead_quote(request: LeadQuoteRequest) -> QuoteResult:
    # 预留给未来“客户线索 + 报价”场景；当前直接复用报价引擎。
    return quote_product(request.spec)

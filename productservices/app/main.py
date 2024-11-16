import json
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, SQLModel, select
from app.db import engine
from app.model import Product, ProductCreate, ProductPublic, ProductUpdate
from aiokafka import AIOKafkaProducer  # type: ignore

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

async def Producer_fn():
    producer = AIOKafkaProducer(bootstrap_servers='broker:9092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@app.post("/products/", response_model=ProductPublic)
async def create_product(product: ProductCreate, producer: Annotated[AIOKafkaProducer, Depends(Producer_fn)]):
    with Session(engine) as session:
        db_product = Product.model_validate(product)
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
    if product.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")

    product_json = json.dumps(product.dict()).encode("utf-8")
    await producer.send_and_wait("product", product_json)

    return db_product

@app.get("/products/", response_model=list[ProductPublic])
def read_products(offset: int = 0, limit: int = Query(default=100, le=100)):
    with Session(engine) as session:
        products = session.exec(select(Product).offset(offset).limit(limit)).all()
        return products

@app.get("/products/{product_id}", response_model=ProductPublic)
def read_product(product_id: int):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

@app.patch("/products/{product_id}", response_model=ProductPublic)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    producer: Annotated[AIOKafkaProducer, Depends(Producer_fn)]
):
    with Session(engine) as session:
        # Fetch the existing product entry from the database
        db_product = session.get(Product, product_id)
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Collect only the fields that are provided in the request (ignoring unset fields)
        update_data = product.model_dump(exclude_unset=True)

        # Manually assign only provided fields to the database model
        for key, value in update_data.items():
            setattr(db_product, key, value)  # Update specific fields

        # Save only the modified fields to the database
        session.commit()
        session.refresh(db_product)  # Get the updated state

    # Send only the updated fields to Kafka to reflect the exact changes
    update_message = json.dumps({"id": db_product.id, "updated_fields": update_data}).encode("utf-8")
    await producer.send_and_wait("product", update_message)

    return db_product



@app.delete("/products/{product_id}")
async def delete_product(product_id: int, producer: Annotated[AIOKafkaProducer, Depends(Producer_fn)]):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        session.delete(product)
        session.commit()
    
    product_json = json.dumps({"id": product_id, "action": "delete"}).encode("utf-8")
    await producer.send_and_wait("product", product_json)

    return {"ok": True}
import asyncio
import json
from fastapi import  FastAPI
from sqlmodel import Session, SQLModel
from aiokafka import AIOKafkaConsumer  # type: ignore
from sqlmodel import create_engine
from sqlmodel import Field, SQLModel


app = FastAPI()

class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: str | None = None
    price: float = Field(..., gt=0)  # Ensures price is greater than 0
    quantity: int = Field(default=0, ge=0)  # Ensures quantity is 0 or more

class Product(ProductBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

sqlite_url = "postgresql://neondb_owner:C8TcsnBawWg6@ep-nameless-mode-a55svycd.us-east-2.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    asyncio.create_task(consumer_product_message())  
async def consumer_product_message():
    consumer = AIOKafkaConsumer(
        'product',
        bootstrap_servers='broker:9092',
        group_id="product_consumer_group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                product_data = json.loads(msg.value.decode("utf-8"))
                with Session(engine) as session:
                    product = Product(**product_data)
                    session.add(product)
                    session.commit()
                print(f"Product {product.name} added to the database.")
            except Exception as e:
                print(f"Error processing message: {e}")
    finally:
        await consumer.stop()


@app.get("/")
def root():
    return {"message": "Product consumer service is running"}       
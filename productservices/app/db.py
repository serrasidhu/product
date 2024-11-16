from sqlmodel import create_engine
sqlite_url = "postgresql://curd_owner:kYdPMv9ADS4i@ep-still-tree-a8au37n4.eastus2.azure.neon.tech/curd?sslmode=require"
engine = create_engine(sqlite_url, echo=True)
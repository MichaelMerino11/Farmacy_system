from sqlalchemy import Column, Integer, String, DateTime, func
from .db import Base

class Muestra(Base):
    __tablename__ = "muestras"

    id = Column(Integer, primary_key=True, index=True)

    nivel = Column(String(50), nullable=False)
    numero_caja = Column(String(50), nullable=False)
    codigo_utn_especie = Column(String(50), nullable=False)
    barcode_image = Column(String(150), nullable=True)
    numero_replica = Column(Integer, nullable=False)
    numero_tubo_en_caja = Column(Integer, nullable=False)
    numero_muestra_ccmbi_ogem = Column(String(50), nullable=False)
    medio_cultivo = Column(String(50), nullable=False)

    ubicacion_refrigerador = Column(String(100), nullable=True)

    codigo_barra = Column(String(80), nullable=False, unique=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
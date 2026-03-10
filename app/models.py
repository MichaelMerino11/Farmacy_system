from sqlalchemy import Column, Integer, String, DateTime, func
from .db import Base


class Caja(Base):
    __tablename__ = "cajas"

    id = Column(Integer, primary_key=True, index=True)
    congelador = Column(Integer, nullable=False)          # 1=vertical, 2=horizontal
    posicion = Column(Integer, nullable=False)            # 1, 2, 3...
    fecha = Column(String(20), nullable=False)            # formato YYYY-MM-DD
    nombre = Column(String(100), nullable=False)
    especie = Column(String(3), nullable=False, server_default="NO")        # SI / NO
    seguimiento = Column(String(3), nullable=False, server_default="NO")   # SI / NO
    identificacion_taxonomica = Column(String(100), nullable=True)
    origen_muestra = Column(String(100), nullable=True)
    codigo_caja = Column(String(300), nullable=True)      # autogenerado
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
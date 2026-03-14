from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from .db import Base


class Caja(Base):
    __tablename__ = "cajas"

    id         = Column(Integer, primary_key=True, index=True)
    congelador = Column(Integer, nullable=False)       # 1=vertical, 2=horizontal
    posicion   = Column(Integer, nullable=False)       # posición en el congelador
    piso       = Column(Integer, nullable=False, default=1)  # piso dentro del congelador
    fecha      = Column(String(20), nullable=False)    # YYYY-MM-DD
    nombre     = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    CAPACIDAD_MAX = 81  # 9x9


class Muestra(Base):
    __tablename__ = "muestras"

    id                        = Column(Integer, primary_key=True, index=True)
    caja_id                   = Column(Integer, ForeignKey("cajas.id"), nullable=True)
    numero_caja               = Column(String(50), nullable=False)   # etiqueta legible ej: CAJA-001
    nivel                     = Column(String(50), nullable=False)   # ej: "Piso 1"
    codigo_utn_especie        = Column(String(50), nullable=False)
    numero_replica            = Column(Integer, nullable=False)
    numero_tubo_en_caja       = Column(Integer, nullable=False)
    numero_muestra_ccmbi_ogem = Column(String(50), nullable=False, unique=True)
    medio_cultivo             = Column(String(50), nullable=False)
    ubicacion_refrigerador    = Column(String(200), nullable=True)
    codigo_barra              = Column(String(80), nullable=False, unique=True, index=True)

    # Campos biológicos — pertenecen a la muestra
    especie                   = Column(String(3), nullable=True, default="NO")   # SI / NO
    seguimiento               = Column(String(3), nullable=True, default="NO")   # SI / NO
    identificacion_taxonomica = Column(String(100), nullable=True, default="")
    origen_muestra            = Column(String(100), nullable=True, default="")
    codigo_para_caja          = Column(String(100), nullable=True, default="")   # autogenerado

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
#!/bin/bash
sqlite3 data.db "
ALTER TABLE cajas ADD COLUMN especie TEXT NOT NULL DEFAULT 'NO';
ALTER TABLE cajas ADD COLUMN seguimiento TEXT NOT NULL DEFAULT 'NO';
ALTER TABLE cajas ADD COLUMN identificacion_taxonomica TEXT;
ALTER TABLE cajas ADD COLUMN origen_muestra TEXT;
ALTER TABLE cajas ADD COLUMN codigo_caja TEXT;
"
echo "Migracion completada."
# TPV - Sistema de Punto de Venta

Sistema de punto de venta desarrollado para un pequeño comercio minorista de alimentación y productos de bazar.

El objetivo del proyecto es sustituir el proceso actual de cobro manual por un sistema sencillo, rápido y fiable que permita:

- Registrar productos.
- Vender productos mediante código EAN.
- Vender frutas y verduras mediante peso introducido manualmente.
- Registrar pagos en efectivo y tarjeta.
- Controlar el stock de productos con EAN.
- Registrar devoluciones.
- Consultar las ventas realizadas.
- Obtener un resumen diario de caja.
- Gestionar usuarios.
- Mantener un historial de operaciones.
- Preparar el sistema para los requisitos españoles de facturación y sistemas informáticos de facturación.

IMPORTANTE: este proyecto es un software propio para un negocio real. La configuración fiscal concreta del negocio debe ser validada con su asesor fiscal antes de utilizar el sistema como sistema de facturación real.

⸻

1. Objetivo del MVP

El MVP debe resolver únicamente el proceso fundamental del negocio:

Empleado inicia sesión
↓
Selecciona productos
↓
Escanea EAN o introduce producto pesable
↓
Se crea el carrito
↓
Se calcula el total
↓
Cliente paga
↓
Se registra la venta
↓
Se actualiza el stock
↓
Se registra el método de pago

El MVP NO pretende inicialmente:

- Integrar una báscula.
- Integrar el datáfono.
- Gestionar contabilidad.
- Gestionar proveedores de forma avanzada.
- Gestionar compras mediante OCR.
- Tener aplicación móvil.
- Tener microservicios.
- Tener Kubernetes.
- Implementar analítica avanzada.
- Gestionar stock de frutas y verduras por peso.
- Sincronizar múltiples tiendas.
- Construir un ERP.

La regla principal es:

Primero conseguir que una venta real pueda realizarse correctamente de principio a fin.

⸻

2. Contexto actual del negocio

El negocio vende principalmente:

Productos con código EAN

Ejemplos:

- Bebidas.
- Productos de limpieza.
- Detergentes.
- Productos envasados.
- Productos de bazar.
- Otros productos con código de barras.

Estos productos sí tendrán:

- EAN.
- Nombre.
- Categoría.
- Precio.
- IVA/tipo fiscal correspondiente.
- Stock.

Frutas y verduras

Ejemplos:

- Tomates.
- Patatas.
- Naranjas.
- Cebollas.
- Etc.

Estos productos se venderán por peso.

Inicialmente:

Producto
↓
Precio por kg
↓
Empleado introduce peso manualmente
↓
Sistema calcula precio

No se controlará inicialmente el stock de frutas y verduras.

⸻

3. Hardware

3.1 Ordenador

El TPV necesita un ordenador capaz de ejecutar:

- Navegador web.
- Aplicación frontend.
- Backend local, si se utiliza arquitectura local.
- PostgreSQL.

La aplicación debe estar diseñada para funcionar correctamente con teclado y ratón.

3.2 Pistola lectora de códigos EAN

El sistema utilizará una pistola/lector de códigos de barras.

La mayoría de lectores de este tipo funcionan como un dispositivo HID/teclado:

Escanear:
8412345678901
El ordenador recibe:
8412345678901

Normalmente el lector añade un Enter al finalizar.

Por tanto, no es necesario implementar una API específica para el lector en el MVP.

El frontend debe disponer de un campo preparado para recibir el EAN:

[ Escanear producto... ]

Flujo:

Lector
↓
Campo de texto
↓
EAN
↓
Enter
↓
Buscar producto
↓
Añadir al carrito

Requisitos del lector

El sistema debe:

- Aceptar códigos EAN-13.
- Permitir introducir EAN manualmente.
- Detectar automáticamente la pulsación Enter.
- Buscar el producto por EAN.
- Añadir el producto al carrito si existe.
- Informar si el EAN no existe.
- Permitir crear el producto si el usuario tiene permisos suficientes.

Recomendación

El campo de escaneo debe mantener el foco después de añadir un producto.

Esto permitirá:

Escanear
Escanear
Escanear
Escanear
Escanear

sin necesidad de tocar el ratón entre productos.

⸻

4. Stack tecnológico

Frontend

- React Puro Javascript
- Vite
- React Router
- CSS / Tailwind CSS, según preferencia
- Cliente HTTP mediante fetch o Axios

Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

Base de datos

- PostgreSQL

Desarrollo

- Git
- GitHub
- Docker
- Docker Compose

Producción futura

AWS:

- S3 + CloudFront para frontend.
- ECS/Fargate para backend.
- RDS PostgreSQL.
- CloudWatch.
- Secrets Manager / Parameter Store.
- HTTPS mediante AWS Certificate Manager.

AWS no forma parte del MVP inicial. Primero debe funcionar correctamente en local.

⸻

5. Arquitectura inicial

La arquitectura inicial será monolítica.

┌─────────────────────┐
│ React │
│ │
└──────────┬──────────┘
│ HTTP
▼
┌─────────────────────┐
│ FastAPI │
│ Python │
└──────────┬──────────┘
│
▼
┌─────────────────────┐
│ PostgreSQL │
└─────────────────────┘

No utilizar microservicios.

No utilizar Kubernetes.

No crear múltiples APIs independientes.

No introducir Redis, Kafka, RabbitMQ, etc. salvo que aparezca una necesidad real.

⸻

6. Entidades principales

El modelo inicial debe contemplar como mínimo:

User
Product
Category
Sale
SaleItem
Payment
StockMovement
Return
ReturnItem
CashSession
Invoice / FiscalRecord

Posteriormente:

Supplier
Purchase
PurchaseItem
AuditLog

⸻

7. Usuarios

Solo existen inicialmente dos empleados.

Campos

## users

id
username
password_hash
role
active
created_at
updated_at

Roles iniciales

ADMIN

Puede:

- Crear productos.
- Modificar productos.
- Desactivar productos.
- Modificar precios.
- Consultar ventas.
- Consultar stock.
- Realizar ajustes de stock.
- Consultar caja.
- Gestionar usuarios.

EMPLOYEE

Puede:

- Iniciar sesión.
- Realizar ventas.
- Realizar devoluciones según permisos definidos.
- Consultar operaciones necesarias para vender.

No puede:

- Modificar configuración fiscal.
- Eliminar ventas.
- Eliminar registros de facturación.
- Modificar registros históricos.
- Gestionar usuarios.

⸻

8. Productos

Productos con EAN

Campos mínimos:

## products

id
ean
name
category_id
price
tax_rate
stock
active
created_at
updated_at

El EAN debe ser único.

Restricción:

UNIQUE(ean)

El producto puede estar:

active = true
active = false

No se debe eliminar físicamente un producto que haya participado en operaciones históricas.

En su lugar:

active = false

Esto preserva el historial.

⸻

9. Categorías

Ejemplos:

Bebidas
Alimentación
Limpieza
Bazar
Fruta
Verdura
Otros

Campos:

## categories

id
name
active

⸻

10. Productos pesables

Los productos de fruta y verdura tendrán un modelo distinto al producto con stock.

Ejemplo:

Tomate
Precio: 2,20 €/kg

Durante una venta:

Peso: 1,350 kg
1,350 × 2,20 = 2,97 €

La venta debe guardar el peso y el precio aplicado.

Ejemplo:

## sale_items

product_id
quantity
unit_price
subtotal
weight

Para productos normales:

quantity = 2
weight = NULL

Para productos pesables:

quantity = 1
weight = 1.350

El diseño exacto puede simplificarse si se decide que todos los artículos pesables utilizan una cantidad decimal.

⸻

11. Dinero

Nunca utilizar float para almacenar dinero.

Incorrecto:

price: float

Preferible:

NUMERIC(10,2)

en PostgreSQL.

Ejemplo:

price NUMERIC(10,2)

Para pesos puede utilizarse:

NUMERIC(10,3)

Ejemplo:

1.350 kg

⸻

12. Carrito

La interfaz principal debe mostrar:

┌────────────────────────────────────────────┐
│ Escanear EAN │
│ [____________________________] │
├────────────────────────────────────────────┤
│ Producto Cant. Precio │
│ Coca-Cola 2 2,40 € │
│ Detergente 1 3,50 € │
│ Tomate 1,350 kg 2,97 € │
├────────────────────────────────────────────┤
│ TOTAL 8,87 € │
│ │
│ [ EFECTIVO ] [ TARJETA ] │
└────────────────────────────────────────────┘

Funciones:

- Añadir producto.
- Incrementar cantidad.
- Reducir cantidad.
- Eliminar producto.
- Vaciar carrito.
- Añadir producto pesable.
- Mostrar subtotal.
- Mostrar total.

⸻

13. Venta

Una venta debe registrar como mínimo:

## sales

id
user_id
total
status
created_at

Estados posibles:

COMPLETED
CANCELLED

No se debe borrar una venta de la base de datos.

Si una venta debe corregirse, se genera una operación posterior que deje constancia de la corrección.

Esto es especialmente importante por los requisitos de integridad y trazabilidad de los sistemas informáticos de facturación. La normativa establece que las correcciones o anulaciones deben conservar el registro original y realizarse mediante registros posteriores. (BOE)

⸻

14. Líneas de venta

## sale_items

id
sale_id
product_id
product_name
quantity
weight
unit_price
tax_rate
subtotal

Es recomendable guardar el nombre y precio utilizados en la operación.

Ejemplo:

Producto actual:
Coca-Cola
Precio actual:
1,30 €
Venta histórica:
Coca-Cola
Precio aplicado:
1,20 €

Modificar el precio actual del producto no debe modificar ventas históricas.

⸻

15. Pagos

Inicialmente solo existen:

CASH
CARD

Tabla:

## payments

id
sale_id
method
amount
created_at

Una venta puede tener inicialmente un único pago.

No es necesario implementar pagos divididos en el MVP.

Ejemplo:

Venta: 15,50 €
CARD
15,50 €

⸻

16. Pago en efectivo

Cuando el cliente paga en efectivo:

Total: 7,80 €
Cliente entrega:
10,00 €
Cambio:
2,20 €

El sistema debe calcular:

change = cash_received - total

Debe rechazar:

cash_received < total

La venta solo se confirma cuando el pago es válido.

⸻

17. Pago con tarjeta

Inicialmente el datáfono NO estará integrado con el software.

Flujo:

Empleado pulsa TARJETA
↓
TPV muestra:
"Procesar pago en datáfono"
↓
Empleado utiliza el datáfono
↓
Pago aceptado
↓
Empleado confirma
↓
Sistema registra venta

El TPV no conocerá inicialmente si el datáfono realmente ha aceptado la operación.

Por tanto, la responsabilidad de confirmar el pago será del empleado.

Una integración real con el datáfono puede añadirse posteriormente si el proveedor ofrece una API/protocolo compatible.

⸻

18. Stock

Solo se controla stock de productos inventariables.

No se controla stock de fruta y verdura en el MVP.

Nunca modificar directamente el stock sin registrar el motivo.

En lugar de:

stock = 25

usar movimientos:

+50 COMPRA
-1 VENTA
-2 MERMA
+3 AJUSTE

Tabla:

## stock_movements

id
product_id
type
quantity
reason
reference_id
user_id
created_at

Tipos:

INITIAL
PURCHASE
SALE
RETURN
LOSS
ADJUSTMENT

⸻

19. Regla de stock

Cuando se completa una venta:

BEGIN TRANSACTION
crear venta
crear líneas
crear pago
crear movimiento de stock
actualizar stock
COMMIT

Si cualquier operación falla:

ROLLBACK

Nunca debe ocurrir:

Venta registrada

- Stock no actualizado

o:

Stock actualizado

- Venta no registrada

La operación debe ser atómica.

⸻

20. Devoluciones

Una devolución nunca debe borrar la venta original.

Ejemplo:

Venta #1543
↓
Producto X
↓
Devolución

Debe existir una operación nueva:

## returns

id
original_sale_id
user_id
total
created_at

Y:

## return_items

id
return_id
sale_item_id
product_id
quantity
amount

La devolución:

- Reduce el dinero de caja.
- Registra la operación.
- Puede devolver stock cuando corresponda.
- Mantiene la venta original.
- Queda asociada al empleado.

⸻

21. Caja

Aunque actualmente no realizan cierre de caja formal, el sistema debe registrar las operaciones.

Debe ser posible consultar:

## Ventas del día

Efectivo: 350,00 €
Tarjeta: 620,00 €
Devoluciones: -15,00 €
Total ventas:
970,00 €

Y:

Efectivo esperado:
350,00 €

Esto no significa necesariamente que el sistema tenga que implementar un arqueo completo en el MVP.

⸻

22. Sesión de caja

Se recomienda crear:

## cash_sessions

id
user_id
opened_at
closed_at
opening_amount
closing_amount
status

Estados:

OPEN
CLOSED

Para el MVP puede permitirse una única caja.

Posteriormente podrá soportarse:

Caja 1
Caja 2

⸻

23. Dashboard diario

Debe existir una pantalla sencilla:

VENTAS DE HOY
Ventas:
42
Efectivo:
350,00 €
Tarjeta:
620,00 €
Devoluciones:
15,00 €
Total:
970,00 €

También:

Productos vendidos:
124
Producto más vendido:
Coca-Cola 330ml

Las estadísticas avanzadas quedan fuera del MVP.

⸻

24. Gestión de productos

Debe existir una pantalla de administración:

Productos
[ Buscar por EAN o nombre ]
EAN Nombre Precio Stock

---

841... Coca-Cola 1,20 € 24
842... Agua 0,80 € 30
843... Detergente 3,50 € 8

Acciones:

- Crear.
- Editar.
- Desactivar.
- Consultar historial.

⸻

25. Alta rápida mediante lector EAN

Cuando se escanee un EAN inexistente:

EAN: 8412345678901
Producto no encontrado.
[ CREAR PRODUCTO ]

Formulario:

EAN
Nombre
Categoría
Precio
IVA
Stock inicial

Al guardar:

crear producto

- crear movimiento INITIAL

⸻

26. Inventario inicial

El negocio actualmente no dispone de un inventario informatizado.

El proceso inicial será:

Escanear producto
↓
Si existe → mostrar
↓
Si no existe → crear
↓
Introducir stock inicial
↓
Guardar

El stock inicial debe quedar registrado como:

INITIAL

No como una modificación silenciosa.

⸻

27. Facturación

Este punto requiere especial cuidado.

El sistema de facturación español establece requisitos de integridad, conservación, accesibilidad, legibilidad, trazabilidad e inalterabilidad de los registros de facturación. Además, el reglamento contempla el encadenamiento de registros y mecanismos como huellas digitales. (BOE)

Por ello:

NO implementar:

DELETE FROM sales

para eliminar ventas facturadas.

NO implementar:

UPDATE sale SET total = ...

para modificar silenciosamente una operación ya registrada.

Las correcciones deben quedar registradas mediante operaciones posteriores.

⸻

28. Facturas simplificadas

Para ventas minoristas existen supuestos en los que puede utilizarse factura simplificada, incluyendo ventas al por menor de hasta 3.000 € IVA incluido, según la información de la AEAT. (Agencia Tributaria)

El sistema debe estar preparado para generar el documento correspondiente.

Debe confirmarse con el asesor fiscal:

- Qué documento debe emitir el negocio.
- Qué numeración debe utilizar.
- Qué series debe utilizar.
- Qué datos fiscales deben aparecer.
- Qué tipos de IVA corresponden a cada producto.
- Si existen operaciones que requieren factura completa.
- Régimen de IVA del negocio.
- Régimen de IRPF.
- Situación respecto al recargo de equivalencia.
- Configuración concreta de VERI\*FACTU.

⸻

29. VERI\*FACTU / SIF

El sistema debe diseñarse desde el principio teniendo en cuenta la normativa española sobre sistemas informáticos de facturación.

Actualmente, la AEAT informa de que los sistemas deben estar adaptados antes del:

1 enero 2027

para contribuyentes del Impuesto sobre Sociedades, y:

1 julio 2027

para los demás obligados que utilicen sistemas informáticos de facturación. (Agencia Tributaria)

El negocio deberá confirmar con su asesor cuál es exactamente su situación.

El MVP no necesita empezar enviando información a la AEAT, pero la arquitectura no debe impedirlo.

⸻

30. Registros de facturación

El diseño debe contemplar posteriormente:

## fiscal_records

id
invoice_id
record_type
sequence_number
timestamp
previous_hash
hash
signature
payload
created_at

El sistema deberá poder mantener la cadena:

Registro 1
↓ hash
Registro 2
↓ hash
Registro 3
↓ hash
Registro 4

De manera que modificar un registro rompa la cadena detectable.

La normativa exige trazabilidad y encadenamiento de los registros de facturación. (BOE)

La implementación definitiva deberá ajustarse a las especificaciones técnicas vigentes en el momento de poner el sistema en producción.

⸻

31. Auditoría

Debe existir una tabla:

## audit_logs

id
user_id
action
entity
entity_id
metadata
created_at

Ejemplos:

PRODUCT_CREATED
PRODUCT_UPDATED
PRODUCT_DEACTIVATED
SALE_CREATED
RETURN_CREATED
STOCK_ADJUSTED
USER_CREATED
USER_UPDATED

Esto permite saber:

Quién
Qué hizo
Sobre qué
Cuándo

⸻

32. Reglas de seguridad

Contraseñas:

NUNCA guardar contraseñas directamente.

Utilizar hashing seguro.

Nunca guardar:

password = "1234"

Utilizar:

password_hash

El backend debe validar permisos.

No confiar en:

role enviado por React

El servidor debe comprobar el usuario autenticado.

⸻

33. API inicial

Endpoints aproximados:

Auth

POST /auth/login
POST /auth/logout
GET /auth/me

Productos

GET /products
GET /products/{id}
GET /products/ean/{ean}
POST /products
PATCH /products/{id}
POST /products/{id}/deactivate

Categorías

GET /categories
POST /categories
PATCH /categories/{id}

Ventas

POST /sales
GET /sales
GET /sales/{id}

Pagos

POST /sales/{id}/payment

Devoluciones

POST /returns
GET /returns
GET /returns/{id}

Stock

GET /stock
GET /stock/{product_id}
POST /stock/adjustments
GET /stock/movements

Caja

POST /cash/open
POST /cash/close
GET /cash/current
GET /cash/daily-summary

⸻

34. Validaciones del backend

El backend debe validar:

- EAN válido.
- EAN único.
- Producto existente.
- Producto activo.
- Precio válido.
- Cantidad positiva.
- Peso positivo.
- Método de pago válido.
- Importe correcto.
- Usuario autorizado.
- Stock suficiente cuando corresponda.
- Venta existente en una devolución.
- Cantidad devuelta válida.
- Totales calculados por el servidor.

Nunca confiar en los totales enviados por React.

Ejemplo:

React puede enviar:

{
"product_id": 10,
"quantity": 2
}

El backend calcula:

precio × cantidad

No debería aceptar ciegamente:

{
"total": 0.01
}

Porque aparentemente los clientes no tardarían ni cinco minutos en descubrirlo.

⸻

35. Transacciones

Crear una venta debe ejecutarse dentro de una transacción PostgreSQL.

Conceptualmente:

BEGIN
validar productos
validar stock
crear venta
crear líneas
crear pago
crear movimientos de stock
COMMIT

Ante cualquier error:

ROLLBACK

⸻

36. Tests

El MVP debe tener tests.

Backend

Testear:

- Login.
- Creación de producto.
- EAN duplicado.
- Búsqueda por EAN.
- Creación de venta.
- Cálculo de totales.
- Pago en efectivo.
- Pago con tarjeta.
- Stock.
- Devoluciones.
- Permisos.
- Transacciones.

Ejemplo

Dado:
Producto = Coca-Cola
Precio = 1,20 €
Stock = 10
Cuando:
Se realiza una venta de 2 unidades
Entonces:
Total = 2,40 €
Stock = 8
Venta registrada
Pago registrado

⸻

37. Docker

El proyecto debe poder iniciarse con:

docker compose up

Servicios:

frontend
backend
postgres

Ejemplo:

docker-compose.yml
services:
frontend:
...
backend:
...
postgres:
...

⸻

38. Variables de entorno

Nunca guardar secretos en Git.

Ejemplo:

DATABASE_URL=
JWT_SECRET=

Utilizar:

.env

y añadirlo a:

.gitignore

⸻

39. Migraciones

Utilizar Alembic.

No modificar manualmente la estructura de producción.

Flujo:

alembic revision --autogenerate
alembic upgrade head

Cada modificación del esquema debe quedar versionada.

⸻

40. Logs

El backend debe registrar errores importantes.

Ejemplo:

2026-09-27 18:42:31
ERROR
Sale creation failed
sale_id=...

Nunca registrar:

- Contraseñas.
- Tokens.
- Secretos.
- Datos sensibles innecesarios.

⸻

41. Backups

PostgreSQL debe tener copias de seguridad.

En local:

pg_dump

En AWS:

RDS automated backups

El sistema debe poder restaurarse.

Un backup que nunca se ha restaurado es una esperanza con formato .sql.

⸻

42. Funcionamiento sin Internet

El negocio actualmente no dispone de Internet.

Por ello, el MVP debe funcionar localmente.

Arquitectura inicial:

Ordenador del TPV
│
├── React
├── FastAPI
└── PostgreSQL

No depender de AWS para realizar una venta.

Posteriormente se podrá diseñar:

TPV local
↓
cola de sincronización
↓
Internet
↓
AWS

Pero la sincronización offline queda fuera del MVP.

⸻

43. AWS

Una vez terminado el MVP:

                         AWS
                    CloudFront
                         │
                         ▼
                         S3
                         │
                      React

                         │
                         ▼
                    ECS/Fargate
                         │
                       FastAPI
                         │
                         ▼
                    RDS PostgreSQL

Servicios adicionales:

CloudWatch
Secrets Manager
ACM
Route 53

AWS no debe introducirse hasta que el sistema local funcione correctamente.

⸻

44. Interfaz

La interfaz debe priorizar velocidad.

Pantallas mínimas:

/login
/pos
/products
/products/new
/products/:id
/sales
/sales/:id
/returns
/stock
/cash
/settings

El empleado debería pasar la mayor parte del tiempo en:

/pos

⸻

45. Atajos de teclado

El TPV debería permitir operar rápidamente.

Ejemplos:

F2 → buscar producto
F4 → efectivo
F5 → tarjeta
ESC → cancelar operación actual
ENTER → confirmar

Los atajos concretos pueden definirse durante las pruebas con los empleados.

⸻

46. Criterios de aceptación del MVP

El MVP se considera funcional cuando se pueda realizar esta secuencia:

1. Iniciar sesión.
2. Escanear un producto EAN.
3. El producto aparece automáticamente.
4. Añadir varias unidades.
5. Escanear otro producto.
6. Añadir fruta/verdura por peso.
7. Calcular correctamente el total.
8. Seleccionar efectivo.
9. Introducir dinero recibido.
10. Calcular cambio.
11. Confirmar venta.
12. Registrar venta.
13. Actualizar stock.
14. Registrar pago.
15. Consultar la venta.
16. Consultar resumen del día.

También:

1. Buscar venta.
2. Seleccionar producto.
3. Crear devolución.
4. Registrar dinero devuelto.
5. Actualizar stock cuando corresponda.
6. Mantener intacta la venta original.

⸻

47. Orden exacto de desarrollo

Fase 1 - Preparación

- Crear repositorio Git.
- Crear README.
- Configurar React.
- Configurar FastAPI.
- Configurar PostgreSQL.
- Configurar Docker Compose.
- Configurar Alembic.
- Configurar estructura de carpetas.

Fase 2 - Base de datos

Crear:

users
categories
products
sales
sale_items
payments
stock_movements
returns
return_items
cash_sessions

Crear relaciones.

Crear índices.

Crear restricciones.

⸻

48. Fase 3 - Autenticación

Implementar:

- Login.
- Hash de contraseñas.
- JWT/sesión.
- Usuario actual.
- Roles.
- Protección de endpoints.

⸻

49. Fase 4 - Productos

Implementar:

- Crear producto.
- Editar producto.
- Desactivar producto.
- Buscar por EAN.
- Buscar por nombre.
- Categorías.
- Precio.
- Stock inicial.

⸻

50. Fase 5 - TPV

Implementar:

- Campo EAN.
- Entrada mediante teclado.
- Entrada mediante scanner.
- Carrito.
- Cantidades.
- Productos pesables.
- Cálculo de totales.
- Eliminación de líneas.

Esta es la primera gran milestone.

⸻

51. Fase 6 - Ventas

Implementar:

- Crear venta.
- Crear líneas.
- Registrar pago.
- Actualizar stock.
- Transacción PostgreSQL.
- Historial de ventas.

⸻

52. Fase 7 - Caja

Implementar:

- Apertura.
- Ventas del día.
- Efectivo.
- Tarjeta.
- Devoluciones.
- Total diario.
- Cierre.

⸻

53. Fase 8 - Devoluciones

Implementar:

- Buscar venta.
- Seleccionar líneas.
- Indicar cantidad.
- Calcular devolución.
- Registrar devolución.
- Actualizar stock.
- Registrar movimiento financiero.

⸻

54. Fase 9 - Inventario

Implementar:

- Stock actual.
- Historial.
- Ajustes.
- Entradas.
- Salidas.
- Mermas.

⸻

55. Fase 10 - Auditoría

Implementar:

- Audit logs.
- Registro de usuario.
- Fecha/hora.
- Operación.
- Entidad afectada.

⸻

56. Fase 11 - Facturación

Antes de implementar esta fase:

Consultar al asesor fiscal.

Confirmar:

Régimen de IVA
Régimen de IRPF
Recargo de equivalencia
Tipos de IVA
Numeración
Series
Factura completa
Factura simplificada
Requisitos del negocio
VERI\*FACTU

Después implementar el modelo fiscal.

⸻

57. Fase 12 - Cumplimiento SIF / VERI\*FACTU

Implementar según las especificaciones vigentes:

- Registros de facturación.
- Encadenamiento.
- Hash.
- Integridad.
- Inalterabilidad.
- Trazabilidad.
- Exportación.
- Firma cuando corresponda.
- QR y contenido requerido cuando corresponda.
- Comunicación con AEAT si se adopta VERI\*FACTU.

La Orden HAC/1177/2024 establece especificaciones técnicas adicionales, incluyendo requisitos relativos a huellas/hash y firma electrónica de registros. (BOE)

No considerar esta fase terminada simplemente porque “la venta funciona”.

⸻

58. Fase 13 - Producción

Una vez validado el sistema:

Docker
↓
AWS
↓
RDS
↓
Backups
↓
HTTPS
↓
Monitoring

Antes de ponerlo en producción:

- Backup probado.
- Restauración probada.
- Usuarios creados.
- Permisos comprobados.
- Datos fiscales comprobados.
- Ventas probadas.
- Devoluciones probadas.
- Stock probado.
- Facturación validada.
- Sistema probado sin Internet si se mantiene la arquitectura local.

⸻

59. Lo que NO entra en el MVP

Queda explícitamente fuera:

- Integración con báscula.
- Integración con datáfono.
- App móvil.
- Multiempresa.
- Multitienda.
- Programa de fidelización.
- Clientes.
- Puntos.
- Promociones complejas.
- Cupones.
- OCR de facturas.
- IA.
- Recomendaciones.
- Predicción de ventas.
- Microservicios.
- Kubernetes.
- Sincronización offline/online.
- Analítica avanzada.

⸻

60. Definition of Done

Una funcionalidad no está terminada porque “funcione en mi ordenador”.

Debe cumplir:

[ ] Código implementado
[ ] Validaciones
[ ] Manejo de errores
[ ] Tests
[ ] Migración DB si procede
[ ] Documentación
[ ] Probada desde frontend
[ ] Probada desde backend
[ ] Probada con datos reales de prueba
[ ] Revisada para permisos
[ ] Sin secretos en Git

⸻

61. Principios del proyecto

62. Los datos históricos no se modifican silenciosamente

Especialmente ventas y registros de facturación.

2. El backend es la autoridad

React muestra y solicita.

FastAPI valida.

PostgreSQL persiste.

3. Las operaciones financieras son transaccionales

Venta + pago + stock deben ser coherentes.

4. No se eliminan datos históricos

Se crean operaciones posteriores que corrigen o compensan.

5. El sistema debe ser sencillo para el empleado

El empleado no debería necesitar saber cómo funciona PostgreSQL.

6. El sistema debe ser mantenible

No construir una arquitectura de cinco años para resolver el problema del primer mes.

7. La normativa fiscal se trata como requisito de negocio

No como un parche que se añade después.

⸻

62. Roadmap

    TPV MVP
    │
    ▼
    ┌──────────────┐
    │ Setup │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ PostgreSQL │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Auth │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Products │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ POS │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Sales │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Payments │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Stock │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Returns │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Cash │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Audit │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Fiscal/SIF │
    └──────┬───────┘
    ▼
    ┌──────────────┐
    │ Production │
    │ AWS │
    └──────────────┘

⸻

63. Primera milestone

La primera versión que debe existir es extremadamente sencilla:

LOGIN
↓
POS
↓
SCAN EAN
↓
PRODUCTO
↓
CARRITO
↓
TOTAL
↓
EFECTIVO / TARJETA
↓
VENTA
↓
STOCK

Si esto funciona correctamente, ya existe un TPV básico.

Todo lo demás se construye alrededor de ese núcleo.

⸻

64. Regla final

No empezar por AWS.

No empezar por VERI\*FACTU.

No empezar por dashboards.

No empezar por diseño visual.

No empezar por la integración de hardware.

Empezar por:

Producto
↓
Venta
↓
Pago
↓
Stock

Ese es el corazón del sistema.

Después se añaden caja, devoluciones, usuarios, auditoría, facturación, cumplimiento fiscal y finalmente infraestructura cloud.

El proyecto debe optimizarse para funcionar correctamente en una tienda real, no para acumular tecnologías en el README.

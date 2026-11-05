# TPV --- Sistema de Punto de Venta

Sistema de punto de venta (TPV) para un pequeño comercio minorista de
alimentación y productos de bazar. El objetivo es sustituir el cobro
manual por una aplicación sencilla, rápida, fiable y preparada para
evolucionar hacia los requisitos españoles de facturación y sistemas
informáticos de facturación (SIF).

> **Aviso fiscal:** este proyecto no debe utilizarse como sistema de
> facturación real hasta que la configuración fiscal y el cumplimiento
> normativo hayan sido validados con el asesor fiscal del negocio. La
> implementación definitiva deberá ajustarse a la normativa y a las
> especificaciones técnicas vigentes en el momento de su puesta en
> producción.

## Objetivos

El sistema debe permitir:

-   Registrar y administrar productos y categorías.
-   Vender productos mediante lectura de códigos EAN-13 o introducción
    manual.
-   Vender frutas y verduras introduciendo manualmente el peso.
-   Crear carritos y calcular importes.
-   Registrar pagos en efectivo y tarjeta.
-   Controlar el stock de productos inventariables.
-   Registrar devoluciones sin borrar la venta original.
-   Consultar ventas e historial de operaciones.
-   Consultar un resumen diario de caja.
-   Gestionar usuarios y permisos.
-   Mantener trazabilidad de las operaciones.
-   Preparar la arquitectura para incorporar facturación y cumplimiento
    SIF/VERI\*FACTU.

## Alcance del MVP

La prioridad es completar correctamente el flujo de una venta real:

1.  El empleado inicia sesión.
2.  Escanea un producto EAN o selecciona un producto pesable.
3.  El sistema añade los artículos al carrito.
4.  Se calcula el total en el servidor.
5.  El cliente paga en efectivo o tarjeta.
6.  Se registra la venta y el pago.
7.  Se actualiza el stock cuando corresponda.
8.  La operación queda disponible en el historial.

El MVP se ejecutará localmente y deberá poder trabajar sin conexión a
Internet.

### Fuera del MVP

No forman parte de la primera versión:

-   Integración con básculas o datáfonos.
-   Aplicación móvil.
-   Contabilidad o gestión avanzada de proveedores y compras.
-   OCR de facturas.
-   Gestión de stock de frutas y verduras por peso.
-   Sincronización entre tiendas o entre entorno local y nube.
-   Multiempresa, multitienda o gestión avanzada de clientes.
-   Fidelización, puntos, cupones y promociones complejas.
-   Analítica avanzada, IA o predicción de ventas.
-   Microservicios, Kubernetes, Redis, Kafka o RabbitMQ.
-   Despliegue en AWS como requisito para realizar ventas.

## Tecnologías

  Capa                    Tecnología
  ----------------------- ----------------------------
  Frontend                React con JavaScript
  Herramientas frontend   Vite, React Router
  Estilos                 CSS o Tailwind CSS
  Comunicación HTTP       Fetch o Axios
  Backend                 Python, FastAPI y Pydantic
  Persistencia y ORM      SQLAlchemy
  Migraciones             Alembic
  Base de datos           PostgreSQL
  Contenedores            Docker y Docker Compose
  Control de versiones    Git y GitHub

La arquitectura inicial será un monolito modular:

``` text
┌─────────────────────┐
│       React         │
│      Frontend       │
└──────────┬──────────┘
           │ HTTP
           ▼
┌─────────────────────┐
│       FastAPI       │
│       Backend       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     PostgreSQL      │
└─────────────────────┘
```

No se introducirán servicios o infraestructuras adicionales sin una
necesidad real.

## Requisitos de ejecución

Para desarrollar y ejecutar el proyecto se necesitará:

-   Docker y Docker Compose.
-   Git.
-   Un navegador web moderno.
-   Un ordenador que pueda ejecutar los contenedores del frontend,
    backend y PostgreSQL.
-   Opcionalmente, un lector de códigos de barras compatible con
    HID/teclado.

El lector de códigos se comporta como un teclado: escribe el EAN en el
campo de escaneo y normalmente envía `Enter` al terminar. Por tanto, no
se necesita una integración específica con el dispositivo para el MVP.

## Puesta en marcha

El proyecto está diseñado para iniciarse en local mediante Docker
Compose.

``` bash
git clone <URL_DEL_REPOSITORIO>
cd <DIRECTORIO_DEL_PROYECTO>
```

Configura las variables de entorno necesarias en un archivo `.env`
(consulta la sección siguiente) y, cuando esté preparado el
`compose.yaml` o `docker-compose.yml`, inicia los servicios:

``` bash
docker compose up --build
```

Los servicios previstos son:

-   `frontend`: aplicación React.
-   `backend`: API FastAPI.
-   `postgres`: base de datos PostgreSQL.

> Los comandos, puertos, scripts y rutas concretos dependerán de la
> configuración real del repositorio. Este README describe la
> arquitectura objetivo; no presupone que todos los servicios estén ya
> implementados.

### Variables de entorno

Los secretos y la configuración local deben mantenerse fuera del control
de versiones. Como mínimo, el backend necesitará variables equivalentes
a:

``` dotenv
DATABASE_URL=
JWT_SECRET=
```

Añade `.env` a `.gitignore`. No incluyas contraseñas, tokens, claves
privadas ni credenciales reales en Git. Los valores de ejemplo deben
documentarse sin utilizar secretos reales.

### Migraciones de base de datos

El esquema de PostgreSQL se gestionará mediante Alembic. Las migraciones
deben versionarse y aplicarse de forma controlada:

``` bash
alembic revision --autogenerate -m "descripcion_del_cambio"
alembic upgrade head
```

No se debe modificar manualmente el esquema de una base de datos de
producción.

## Funcionalidades y reglas de negocio

### Productos con EAN

Los productos inventariables tendrán, como mínimo:

-   EAN único.
-   Nombre.
-   Categoría.
-   Precio.
-   Tipo o porcentaje fiscal.
-   Stock.
-   Estado activo/inactivo.
-   Fechas de creación y actualización.

El EAN debe tener una restricción de unicidad. Los productos que ya
formen parte de operaciones históricas no se eliminarán físicamente: se
desactivarán para conservar la trazabilidad.

Si se escanea un EAN inexistente, el sistema informará del resultado y
permitirá iniciar el alta rápida si el usuario tiene permisos. El stock
inicial se registrará mediante un movimiento `INITIAL`, no mediante una
modificación silenciosa.

### Frutas y verduras por peso

Los productos pesables se venderán introduciendo manualmente el peso. El
sistema calculará el importe a partir del peso y del precio por
kilogramo.

Ejemplo:

``` text
Producto: Tomate
Precio:   2,20 €/kg
Peso:     1,350 kg
Total:    2,97 €
```

La línea de venta debe conservar el peso y el precio aplicado. En el MVP
no se controlará el stock de frutas y verduras.

### Carrito y lector EAN

La pantalla de TPV debe priorizar la velocidad de operación. Debe
permitir añadir artículos, incrementar o reducir cantidades, eliminar
líneas, vaciar el carrito, introducir productos pesables y consultar
subtotales y total.

El campo de escaneo debe aceptar entrada del lector o del teclado,
procesar el EAN al recibir `Enter` y recuperar el foco después de añadir
un producto para facilitar el escaneo consecutivo.

Atajos previstos, pendientes de validar con los empleados:

  Tecla     Acción
  --------- ------------------------------
  `F2`      Buscar producto
  `F4`      Seleccionar efectivo
  `F5`      Seleccionar tarjeta
  `ESC`     Cancelar la operación actual
  `ENTER`   Confirmar

### Pagos

Los métodos iniciales son:

-   `CASH`: efectivo.
-   `CARD`: tarjeta.

En el MVP cada venta tendrá un único pago. No se contemplan pagos
divididos.

Para efectivo, el sistema calculará el cambio:

``` text
cambio = efectivo_recibido - total
```

Se rechazará cualquier pago en efectivo inferior al total. La venta solo
se confirmará cuando el pago sea válido.

Para tarjeta, el empleado procesará el cobro en el datáfono externo y
confirmará manualmente en el TPV que el pago ha sido aceptado. El
software no verificará automáticamente la operación del datáfono.

### Ventas y líneas de venta

Una venta conservará el usuario responsable, el total, el estado y la
fecha de creación. Los estados iniciales serán `COMPLETED` y
`CANCELLED`.

Las líneas deben guardar una copia de los datos relevantes utilizados en
el momento de la operación, como nombre del producto, precio unitario y
tipo fiscal. Cambiar posteriormente el nombre o el precio del catálogo
no debe alterar el historial.

Las ventas no se borrarán. Las correcciones se registrarán mediante
operaciones posteriores, conservando la operación original.

### Stock

Solo se controlará el stock de productos inventariables. Toda variación
deberá generar un movimiento con tipo, cantidad, motivo, referencia,
usuario y fecha.

Tipos de movimiento previstos:

-   `INITIAL`
-   `PURCHASE`
-   `SALE`
-   `RETURN`
-   `LOSS`
-   `ADJUSTMENT`

La creación de una venta, sus líneas, el pago, los movimientos de stock
y la actualización de existencias deben realizarse en una única
transacción de base de datos. Si una parte falla, se ejecutará
`ROLLBACK`; no puede quedar registrada una venta sin su actualización de
stock correspondiente, ni actualizarse el stock sin registrar la venta.

### Devoluciones

Una devolución será una operación nueva asociada a la venta original y
al empleado que la registra. Debe identificar las líneas y cantidades
devueltas, calcular el importe y registrar el efecto financiero y,
cuando corresponda, el movimiento de stock.

La venta original permanecerá intacta. También deberán validarse la
existencia de la venta, las cantidades disponibles para devolver y el
importe correspondiente.

### Caja y resumen diario

El sistema permitirá consultar las ventas del día, importes cobrados en
efectivo y tarjeta, devoluciones y total diario. También se contempla
una sesión de caja con apertura, cierre, importe inicial, importe final
y estado.

El MVP puede comenzar con una única caja. El resumen diario no implica
necesariamente implementar desde el inicio un proceso completo de
arqueo.

### Usuarios y permisos

Roles iniciales:

**ADMIN**

-   Crear, modificar y desactivar productos.
-   Modificar precios.
-   Consultar ventas y stock.
-   Realizar ajustes de stock.
-   Consultar caja.
-   Gestionar usuarios.

**EMPLOYEE**

-   Iniciar sesión.
-   Realizar ventas.
-   Realizar devoluciones según los permisos definidos.
-   Consultar la información necesaria para vender.

El empleado no podrá modificar la configuración fiscal, eliminar ventas,
eliminar registros de facturación, modificar registros históricos ni
gestionar usuarios.

Los permisos se validarán siempre en el backend. Nunca se confiará en un
rol enviado por React.

## Modelo de datos inicial

Las entidades principales previstas son:

  -----------------------------------------------------------------------
  Entidad                             Responsabilidad
  ----------------------------------- -----------------------------------
  `users`                             Usuarios, credenciales cifradas
                                      mediante hash, rol y estado

  `categories`                        Categorías de productos

  `products`                          Catálogo, EAN, precio, tipo fiscal
                                      y stock

  `sales`                             Cabecera de las ventas

  `sale_items`                        Líneas y datos históricos de cada
                                      artículo vendido

  `payments`                          Método e importe de cada pago

  `stock_movements`                   Historial de entradas y salidas de
                                      inventario

  `returns`                           Cabecera de las devoluciones

  `return_items`                      Líneas devueltas

  `cash_sessions`                     Apertura y cierre de caja

  `fiscal_records`                    Registros de facturación y
                                      encadenamiento futuro

  `audit_logs`                        Trazabilidad de acciones relevantes
  -----------------------------------------------------------------------

`Supplier`, `Purchase` y `PurchaseItem` podrán incorporarse
posteriormente si se implementa una gestión de proveedores y compras más
avanzada.

### Consideraciones de persistencia

-   El EAN será único.
-   Los importes monetarios se almacenarán con tipos decimales, por
    ejemplo `NUMERIC(10,2)`, nunca con `float`.
-   Los pesos podrán almacenarse con precisión de tres decimales, por
    ejemplo `NUMERIC(10,3)`.
-   Se definirán claves foráneas, restricciones e índices adecuados.
-   Los datos históricos no se modificarán silenciosamente.
-   Las operaciones financieras y de stock serán transaccionales.

## API prevista

Los siguientes endpoints representan la API inicial prevista; pueden
ajustarse durante la implementación.

  Área            Método    Endpoint
  --------------- --------- -----------------------------
  Autenticación   `POST`    `/auth/login`
  Autenticación   `POST`    `/auth/logout`
  Autenticación   `GET`     `/auth/me`
  Productos       `GET`     `/products`
  Productos       `GET`     `/products/{id}`
  Productos       `GET`     `/products/ean/{ean}`
  Productos       `POST`    `/products`
  Productos       `PATCH`   `/products/{id}`
  Productos       `POST`    `/products/{id}/deactivate`
  Categorías      `GET`     `/categories`
  Categorías      `POST`    `/categories`
  Categorías      `PATCH`   `/categories/{id}`
  Ventas          `POST`    `/sales`
  Ventas          `GET`     `/sales`
  Ventas          `GET`     `/sales/{id}`
  Pagos           `POST`    `/sales/{id}/payment`
  Devoluciones    `POST`    `/returns`
  Devoluciones    `GET`     `/returns`
  Devoluciones    `GET`     `/returns/{id}`
  Stock           `GET`     `/stock`
  Stock           `GET`     `/stock/{product_id}`
  Stock           `POST`    `/stock/adjustments`
  Stock           `GET`     `/stock/movements`
  Caja            `POST`    `/cash/open`
  Caja            `POST`    `/cash/close`
  Caja            `GET`     `/cash/current`
  Caja            `GET`     `/cash/daily-summary`

### Validaciones del backend

FastAPI será la autoridad para validar, entre otros aspectos:

-   Formato y unicidad del EAN.
-   Existencia y estado activo del producto.
-   Precio, cantidad y peso positivos.
-   Método e importe del pago.
-   Identidad y permisos del usuario.
-   Stock suficiente cuando corresponda.
-   Existencia de la venta original y cantidades válidas en una
    devolución.
-   Cálculo de líneas, impuestos y totales.

El frontend enviará los datos necesarios para solicitar una operación,
pero nunca será la autoridad para determinar su importe final. Los
totales se calcularán y validarán en el servidor.

## Seguridad, auditoría y registros

-   Las contraseñas nunca se almacenarán en texto plano; se utilizará
    hashing seguro.
-   La autenticación se realizará mediante JWT o un mecanismo de sesión
    adecuado.
-   Los endpoints protegidos comprobarán la identidad y los permisos en
    el backend.
-   Las acciones relevantes quedarán registradas en `audit_logs`,
    incluyendo usuario, acción, entidad afectada, identificador,
    metadatos y fecha.
-   Se registrarán errores importantes del backend.
-   Los logs no incluirán contraseñas, tokens, secretos ni datos
    sensibles innecesarios.
-   Los secretos se gestionarán mediante variables de entorno y nunca se
    subirán al repositorio.

Acciones de auditoría previstas: `PRODUCT_CREATED`, `PRODUCT_UPDATED`,
`PRODUCT_DEACTIVATED`, `SALE_CREATED`, `RETURN_CREATED`,
`STOCK_ADJUSTED`, `USER_CREATED` y `USER_UPDATED`.

## Facturación y cumplimiento fiscal en España

El diseño debe contemplar los requisitos de integridad, conservación,
accesibilidad, legibilidad, trazabilidad e inalterabilidad de los
registros de facturación, así como el encadenamiento de registros y las
huellas digitales que correspondan.

El sistema debe poder evolucionar para incorporar:

-   Registros de facturación.
-   Numeración y series.
-   Encadenamiento de registros y hashes.
-   Integridad e inalterabilidad.
-   Exportación y firma cuando corresponda.
-   Código QR y contenido exigido, cuando corresponda.
-   Comunicación con la AEAT si se adopta la modalidad VERI\*FACTU.

Antes de implementar esta parte, el negocio debe confirmar con su asesor
fiscal el régimen aplicable, los tipos de IVA, el IRPF, el posible
recargo de equivalencia, los documentos que debe emitir, las series y
numeración, y si corresponde emitir factura simplificada o completa.

La documentación de partida indica como fechas de adaptación el 1 de
enero de 2027 para contribuyentes del Impuesto sobre Sociedades y el 1
de julio de 2027 para los demás obligados que utilicen sistemas
informáticos de facturación. Estas fechas y su aplicabilidad concreta
deben verificarse con el asesor fiscal y las fuentes oficiales antes de
planificar la puesta en producción.

**No se considerará que el sistema cumple la normativa por el mero hecho
de registrar ventas.** La fase SIF/VERI\*FACTU requiere una
implementación y validación específicas conforme a las disposiciones
vigentes.

## Pruebas

El MVP debe incluir pruebas automatizadas del backend, como mínimo para:

-   Inicio de sesión y permisos.
-   Creación de productos y detección de EAN duplicados.
-   Búsqueda por EAN.
-   Creación de ventas y cálculo de totales.
-   Pagos en efectivo y tarjeta.
-   Actualización y consistencia del stock.
-   Devoluciones.
-   Transacciones y rollback ante errores.

Ejemplo de comportamiento esperado:

``` text
Dado:
  Producto: Coca-Cola
  Precio:   1,20 €
  Stock:    10

Cuando:
  Se venden 2 unidades

Entonces:
  Total:             2,40 €
  Stock restante:    8
  Venta registrada
  Pago registrado
```

## Copias de seguridad y recuperación

PostgreSQL debe disponer de copias de seguridad periódicas. En local se
contempla `pg_dump`; en una futura infraestructura AWS se podrán
utilizar las copias automatizadas de RDS.

No basta con generar copias: debe probarse periódicamente su
restauración para comprobar que los datos pueden recuperarse.

## Funcionamiento local y evolución a AWS

El negocio no dispone actualmente de Internet. Por ello, el MVP debe
ejecutar frontend, backend y PostgreSQL en el entorno local y no
depender de AWS para realizar una venta.

AWS queda para una fase posterior, una vez validado el funcionamiento
local. La arquitectura futura prevista contempla:

-   S3 y CloudFront para el frontend.
-   ECS/Fargate para FastAPI.
-   RDS PostgreSQL.
-   CloudWatch para monitorización.
-   Secrets Manager o Parameter Store para secretos y configuración.
-   AWS Certificate Manager para HTTPS.
-   Route 53 para DNS, si procede.

La sincronización entre un TPV local y la nube no forma parte del MVP.

## Pantallas previstas

  Ruta              Pantalla
  ----------------- ---------------------------------
  `/login`          Inicio de sesión
  `/pos`            Punto de venta
  `/products`       Listado y búsqueda de productos
  `/products/new`   Alta de producto
  `/products/:id`   Detalle y edición de producto
  `/sales`          Historial de ventas
  `/sales/:id`      Detalle de venta
  `/returns`        Devoluciones
  `/stock`          Inventario y movimientos
  `/cash`           Caja y resumen diario
  `/settings`       Configuración

La pantalla `/pos` será el centro de trabajo del empleado y debe
optimizarse para operar principalmente con lector EAN y teclado.

## Plan de desarrollo

El orden de implementación recomendado es:

1.  **Preparación:** repositorio, React, FastAPI, PostgreSQL, Docker
    Compose, Alembic y estructura del proyecto.
2.  **Base de datos:** entidades iniciales, relaciones, índices y
    restricciones.
3.  **Autenticación:** login, hashing, sesión o JWT, usuario actual,
    roles y protección de endpoints.
4.  **Productos:** altas, edición, desactivación, categorías, búsqueda
    por EAN/nombre y stock inicial.
5.  **TPV:** campo EAN, lector, carrito, cantidades, productos pesables
    y totales.
6.  **Ventas:** cabecera, líneas, pagos, stock, transacciones e
    historial.
7.  **Caja:** apertura, resumen diario, desglose por método de pago y
    cierre.
8.  **Devoluciones:** búsqueda de venta, selección de líneas, cálculo,
    registro financiero y stock.
9.  **Inventario:** consulta, historial, ajustes, entradas, salidas y
    mermas.
10. **Auditoría:** acciones, usuario, fecha y entidad afectada.
11. **Facturación:** definición y validación de la configuración fiscal
    con el asesor.
12. \*\*SIF/VERI\*FACTU:\*\* implementación de requisitos técnicos y
    legales aplicables.
13. **Producción:** despliegue, backups, restauración, HTTPS y
    monitorización.

La primera milestone funcional debe limitarse a:

``` text
LOGIN
  ↓
POS
  ↓
ESCANEAR EAN
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
```

## Criterios de aceptación del MVP

El MVP se considerará funcional cuando se pueda:

1.  Iniciar sesión con un usuario autorizado.
2.  Escanear un EAN y añadir el producto encontrado al carrito.
3.  Añadir varias unidades y escanear otros productos sin perder el foco
    del campo.
4.  Añadir frutas o verduras introduciendo su peso.
5.  Calcular correctamente el total.
6.  Cobrar en efectivo, introducir el importe recibido y calcular el
    cambio.
7.  Confirmar un pago con tarjeta mediante confirmación manual del
    empleado.
8.  Registrar la venta, sus líneas y el pago.
9.  Actualizar el stock de productos inventariables de forma atómica.
10. Consultar la venta y el resumen diario.
11. Localizar una venta y registrar una devolución sin modificar la
    venta original.
12. Reflejar el efecto de la devolución en caja y en stock cuando
    corresponda.

## Definition of Done

Una funcionalidad no se considerará terminada únicamente porque funcione
en el entorno del desarrollador. Debe cumplir los siguientes puntos:

-   [ ] Código implementado.
-   [ ] Validaciones de entrada y reglas de negocio.
-   [ ] Manejo de errores.
-   [ ] Tests automatizados.
-   [ ] Migración de base de datos, si procede.
-   [ ] Documentación actualizada.
-   [ ] Prueba desde el frontend.
-   [ ] Prueba desde el backend.
-   [ ] Prueba con datos de prueba representativos.
-   [ ] Permisos comprobados.
-   [ ] Ausencia de secretos en Git.

## Principios de diseño

1.  **Los datos históricos no se modifican silenciosamente.** Las
    correcciones se registran mediante nuevas operaciones.
2.  **El backend es la autoridad.** React presenta información y
    solicita operaciones; FastAPI valida y PostgreSQL persiste.
3.  **Las operaciones financieras son transaccionales.** Venta, pago y
    stock deben mantener la coherencia.
4.  **No se eliminan datos históricos.** Se conservan las operaciones
    originales y se registran sus correcciones.
5.  **La interfaz debe ser rápida y sencilla.** El empleado no necesita
    conocer los detalles internos del sistema.
6.  **La arquitectura debe ser mantenible.** No se incorporará
    complejidad tecnológica sin una necesidad demostrable.
7.  **La normativa fiscal es un requisito de negocio.** No debe tratarse
    como un parche añadido al final.

## Estado del proyecto

Este documento describe los requisitos y el alcance objetivo del
proyecto. No implica que todas las funcionalidades, endpoints,
migraciones o servicios estén implementados actualmente.

El criterio de prioridad es claro: primero debe funcionar de forma
fiable el ciclo **producto → venta → pago → stock**. Después se
incorporarán caja, devoluciones, inventario, usuarios, auditoría,
facturación, cumplimiento fiscal y, finalmente, infraestructura cloud.

# Backend de Korrijo

En primer lugar se debe crear (y activar) un entorno virtual de Python e instalar las dependencias. Esto último se hace así:

pip install --upgrade pip
pip install -r requirements-dev.txt

Para arrancar el servidor:

uvicorn app.main:app --reload

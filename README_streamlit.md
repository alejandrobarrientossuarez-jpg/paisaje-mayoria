# Paisaje de atractores del autómata de mayoría — app en Streamlit

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `paisaje_mayoria.py` | Motor de cálculo (red, regla, F, puntos fijos, periódicos, atractores, cuencas, paisaje). Funciona solo en consola. |
| `app.py` | Interfaz Streamlit: importa el motor y lo muestra en pestañas. |
| `requirements.txt` | Dependencias (solo `streamlit`). |

Los tres archivos deben estar en la misma carpeta.

## 1. Probar en tu computadora

```bash
pip install streamlit
streamlit run app.py
```

Se abre el navegador en http://localhost:8501. En la barra lateral se elige {0,1}^1, {0,1}^4, {0,1}^9 o {0,1}^16; las pestañas muestran la red, el autómata, los puntos fijos, los puntos periódicos con su período, los atractores, las cuencas (con sus niveles), el resumen del paisaje y la trayectoria de cualquier configuración que se escriba. El botón de la barra lateral descarga el reporte completo en .txt.

## 2. Publicar en Streamlit Community Cloud (gratis)

1. Crea un repositorio en GitHub (público o privado) y sube `app.py`, `paisaje_mayoria.py` y `requirements.txt` a la raíz del repositorio.
2. Entra en https://share.streamlit.io e inicia sesión con tu cuenta de GitHub (la primera vez te pedirá autorizar a Streamlit).
3. Pulsa **Create app** (esquina superior derecha) y responde **"Yup, I have an app"**.
4. Indica el repositorio, la rama (normalmente `main`) y el archivo principal: `app.py`. Opcionalmente elige un subdominio; la app quedará en `https://<subdominio>.streamlit.app`.
5. Pulsa **Deploy**. La primera vez tarda uno o dos minutos. Cada vez que hagas `git push` al repositorio, la app se actualiza sola.

Notas:
- Community Cloud da alrededor de 1 GB de memoria por app. Las rejillas 1×1 a 4×4 caben sin problema (4×4 tarda unos 3 segundos la primera vez y luego queda en caché). La rejilla 5×5 no se ofrece en la app porque necesita 2 GB.
- Si el repositorio es privado, en Settings → Linked accounts hay que dar a Streamlit permiso sobre repositorios privados.
- Los registros (logs) de la app se ven desde el menú "Manage app" cuando estás conectado con tu cuenta.

## 3. Alternativa: Hugging Face Spaces

En https://huggingface.co/new-space crea un Space con SDK "Streamlit", sube los tres archivos y listo. Es útil si prefieres no usar GitHub.

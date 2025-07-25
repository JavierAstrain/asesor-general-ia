import streamlit as st
import pandas as pd
import google.generativeai as genai
import io # Para manejar archivos en memoria

# --- Configuración de Autenticación ---
CORRECT_USERNAME = "javi"
CORRECT_PASSWORD = "javi"

# Configuración de la API de Gemini
# La clave API se inyectará en tiempo de ejecución en el entorno de Canvas.
# Si ejecutas esto localmente, necesitarás establecer la variable de entorno
# GOOGLE_API_KEY o reemplazar "" con tu clave API.
# Ahora se lee desde st.secrets, que puede ser configurado localmente en .streamlit/secrets.toml
# o en el panel de control de Streamlit Cloud.
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("Error: La clave API de Gemini no está configurada en Streamlit Secrets. "
             "Por favor, añade 'GOOGLE_API_KEY' a tu archivo .streamlit/secrets.toml "
             "o configúrala en el panel de control de Streamlit Cloud.")
    st.stop() # Detiene la ejecución de la aplicación si la clave no está disponible

genai.configure(api_key=API_KEY)

# Inicializar el modelo de Gemini
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Configuración de Streamlit ---
st.set_page_config(
    page_title="Gerente General IA", # Título actualizado
    page_icon="🤖", # Icono actualizado para reflejar un bot más general
    layout="wide"
)

# Estilo personalizado con Tailwind CSS (simulado con Markdown y HTML)
st.markdown("""
    <style>
    .reportview-container {
        background: linear-gradient(to bottom right, #e0f2fe, #ede9fe);
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5%;
        padding-right: 5%;
    }
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #1e40af;
    }
    /* Estilos de mensajes de chat (mantener para consistencia, aunque no se usen directamente en el flujo) */
    .chat-message-user {
        background-color: #3b82f6; /* blue-500 */
        color: white;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        margin-left: auto;
        max-width: 80%;
        border-bottom-right-radius: 0;
    }
    .chat-message-ai {
        background-color: #e5e7eb; /* gray-200 */
        color: #1f2937; /* gray-800 */
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        margin-right: auto;
        max-width: 80%;
        border-bottom-left-radius: 0;
    }
    .chat-message-system {
        background-color: #fffbeb; /* yellow-100 */
        color: #374151; /* gray-700 */
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        text-align: center;
        font-size: 0.875rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Gestión de estado de la sesión ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "excel_data" not in st.session_state:
    st.session_state.excel_data = None
if "google_sheet_url" not in st.session_state:
    st.session_state.google_sheet_url = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "last_ai_response" not in st.session_state:
    st.session_state.last_ai_response = "Esperando tu primera pregunta..."


# --- Funciones de procesamiento de datos ---

def process_excel_file(uploaded_file):
    """Procesa un archivo Excel cargado y devuelve un DataFrame."""
    try:
        df = pd.read_excel(uploaded_file)
        st.session_state.excel_data = df
        st.session_state.chat_history.append({"role": "system", "content": f"Archivo Excel '{uploaded_file.name}' cargado y procesado. Ahora puedes hacer preguntas sobre los datos."})
        return True
    except Exception as e:
        st.session_state.chat_history.append({"role": "system", "content": f"Error al procesar el archivo Excel: {e}"})
        return False

def process_google_sheet_url(url):
    """
    Simula el procesamiento de una URL de Google Sheet.
    La integración real requeriría autenticación y la API de Google Sheets.
    """
    if not url.strip():
        st.session_state.chat_history.append({"role": "system", "content": "Por favor, introduce una URL de Google Sheet válida."})
        return False

    st.session_state.google_sheet_url = url
    st.session_state.chat_history.append({"role": "system", "content": f"URL de Google Sheet '{url}' guardada. En una aplicación real, se conectaría a esta hoja."})
    return True

# --- Interacción con la IA ---

def get_ai_response(user_message):
    """Envía el mensaje del usuario y el contexto de datos a Gemini y obtiene una respuesta."""
    # La clave API ya se verifica al inicio de la aplicación
    
    full_prompt = user_message

    # Añadir contexto de datos si está disponible
    data_context = ""
    if st.session_state.excel_data is not None:
        # Generar un resumen de la estructura y una muestra de los datos
        buffer = io.StringIO()
        st.session_state.excel_data.info(buf=buffer, verbose=True)
        data_info = buffer.getvalue()

        data_context += "\n\nEl usuario ha cargado una planilla Excel con la siguiente estructura y una muestra de datos:\n"
        data_context += "--- Información de la Planilla ---\n"
        data_context += data_info
        data_context += "\n--- Primeras 5 filas ---\n"
        data_context += st.session_state.excel_data.head().to_markdown(index=False)
        data_context += "\n--- Últimas 5 filas ---\n"
        data_context += st.session_state.excel_data.tail().to_markdown(index=False)
        data_context += "\n\n"
        data_context += "Considera que esta es una muestra representativa de la planilla completa. "
        data_context += "Si necesitas datos específicos o realizar cálculos sobre la planilla completa, por favor, indícalo claramente. "
        data_context += "Puedo ayudarte a consultar información, hacer cálculos y dar recomendaciones más allá del contexto directo de los datos, actuando como un Gerente General IA."

    if st.session_state.google_sheet_url is not None:
        data_context += f"\n\nEl usuario ha vinculado la siguiente URL de Google Sheet: {st.session_state.google_sheet_url}. "
        data_context += "Considera que esta es una fuente de datos adicional."

    if data_context:
        full_prompt = f"{data_context}\n\nConsulta del usuario: {user_message}"

    try:
        # Preparar el historial para Gemini
        gemini_chat_history = []
        # Limitar el historial para evitar exceder el límite de tokens
        # Mantener solo los últimos 10 mensajes (5 pares de usuario/AI)
        recent_history = st.session_state.chat_history[-10:]
        for msg in recent_history:
            if msg["role"] == "user":
                gemini_chat_history.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "ai":
                gemini_chat_history.append({"role": "model", "parts": [{"text": msg["content"]}]})

        # Iniciar el chat con el historial
        chat = model.start_chat(history=gemini_chat_history)
        response = chat.send_message(full_prompt)

        if response.text:
            return response.text
        else:
            return "Lo siento, la IA no pudo generar una respuesta significativa."
    except genai.types.BlockedPromptException as e:
        st.error(f"Error de seguridad: La consulta fue bloqueada por las políticas de seguridad de la IA. Por favor, reformula tu pregunta. Detalles: {e}")
        return "Lo siento, tu consulta fue bloqueada por razones de seguridad. Por favor, intenta con una pregunta diferente."
    except Exception as e:
        st.error(f"Error al obtener respuesta de la IA: {e}")
        return "Hubo un error al conectar con la IA. Por favor, inténtalo de nuevo."

# --- Lógica de Autenticación ---
if not st.session_state.logged_in:
    st.title("Acceso al Gerente General IA")
    st.markdown("---")

    username = st.text_input("Usuario", key="login_username")
    password = st.text_input("Contraseña", type="password", key="login_password")

    if st.button("Iniciar Sesión", key="login_button"):
        if username == CORRECT_USERNAME and password == CORRECT_PASSWORD:
            st.session_state.logged_in = True
            st.success("¡Sesión iniciada correctamente!")
            st.rerun() # Forzar un re-render para mostrar la aplicación principal
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.stop() # Detiene la ejecución si no está logueado

# --- Diseño de la aplicación Streamlit (solo si está logueado) ---
st.title("🤖 Gerente General IA") # Título principal actualizado

# Sección de Carga de Datos en un expander
with st.expander("Cargar Datos para el Gerente General IA"): # Texto del expander actualizado
    st.subheader("Archivo Excel (.xlsx, .xls)")
    uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"], key="excel_uploader")
    if uploaded_file is not None:
        if st.button("Procesar Excel", key="process_excel_btn"):
            with st.spinner("Procesando archivo Excel..."):
                process_excel_file(uploaded_file)
            st.rerun() # Forzar re-render para mostrar el mensaje del sistema

    st.markdown("---")

    st.subheader("Vincular Google Sheet (URL)")
    google_sheet_input = st.text_input("Introduce la URL de tu Google Sheet", key="google_sheet_url_input")
    if st.button("Vincular Hoja", key="link_sheet_btn"):
        with st.spinner("Vinculando Google Sheet..."):
            process_google_sheet_url(google_sheet_input)
        st.rerun() # Forzar re-render para mostrar el mensaje del sistema

    st.markdown("---")

    if st.button("Reiniciar Datos Cargados", help="Borra los datos de Excel y la URL de Google Sheet de la sesión.", key="reset_data_btn"):
        st.session_state.excel_data = None
        st.session_state.google_sheet_url = None
        st.session_state.chat_history.append({"role": "system", "content": "Datos de carga reiniciados."})
        st.rerun() # Forzar un re-render para limpiar los widgets

# Área de visualización del chat
chat_placeholder = st.container()
with chat_placeholder:
    if not st.session_state.chat_history:
        st.markdown("""
            <div class="chat-message-system">
                ¡Hola! Soy tu Gerente General IA. ¿En qué puedo ayudarte hoy?
                <br/>
                Puedes preguntarme sobre finanzas, marketing, operaciones, recursos humanos y más, basándome en los datos que cargues.
            </div>
        """, unsafe_allow_html=True)
    else:
        # Mostrar la última respuesta de la IA aquí
        st.markdown(f'<div class="chat-message-ai">{st.session_state.last_ai_response}</div>', unsafe_allow_html=True)


# Entrada de texto para el chat
user_input = st.chat_input("Escribe tu pregunta o comentario...", key="user_input_chat")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.spinner("Pensando..."):
        ai_response = get_ai_response(user_input)
        st.session_state.last_ai_response = ai_response # Guardar la última respuesta
        st.session_state.chat_history.append({"role": "ai", "content": ai_response})
    st.rerun() # Forzar un re-render para mostrar el nuevo mensaje

# Vista previa de datos cargados (debajo del chat input)
if st.session_state.excel_data is not None:
    st.subheader("Vista Previa de Datos Excel Cargados")
    st.dataframe(st.session_state.excel_data) # Mostrar el DataFrame completo
    st.caption("Nota: El modelo de IA recibe un resumen de la estructura y una muestra de los datos. Para consultas muy específicas que requieran datos fuera de la muestra, la IA podría necesitar que especifiques qué información necesitas.")

if st.session_state.google_sheet_url is not None:
    st.subheader("Detalles de Google Sheet Vinculado")
    st.success(f"Google Sheet vinculado: {st.session_state.google_sheet_url}")
    st.info("Nota: La integración real de Google Sheets requeriría autenticación.")

# --- Registro de Preguntas del Usuario (Nuevo) ---
st.subheader("Historial de Preguntas")
if any(msg["role"] == "user" for msg in st.session_state.chat_history):
    for i, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(f"- **Pregunta {i+1}:** {message['content']}")
else:
    st.info("Aún no has realizado ninguna pregunta.")

import streamlit as st
import pandas as pd
import google.generativeai as genai
import io # Para manejar archivos en memoria

# Configuración de la API de Gemini
# La clave API se inyectará en tiempo de ejecución en el entorno de Canvas.
# Si ejecutas esto localmente, necesitarás establecer la variable de entorno
# GOOGLE_API_KEY o reemplazar "" con tu clave API.
API_KEY = "" # Reemplaza con tu clave API si no estás en Canvas
genai.configure(api_key=API_KEY)

# Inicializar el modelo de Gemini
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Configuración de Streamlit ---
st.set_page_config(
    page_title="Asesor Financiero con IA",
    page_icon="💰",
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

# --- Funciones de procesamiento de datos ---

def process_excel_file(uploaded_file):
    """Procesa un archivo Excel cargado y devuelve un DataFrame."""
    try:
        df = pd.read_excel(uploaded_file)
        # Aquí podrías realizar limpieza, validación o selección de columnas
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
    
    # Aquí iría la lógica real para acceder a Google Sheets.
    # Por ahora, solo almacenamos la URL y simulamos el éxito.
    st.session_state.google_sheet_url = url
    st.session_state.chat_history.append({"role": "system", "content": f"URL de Google Sheet '{url}' guardada. En una aplicación real, se conectaría a esta hoja."})
    return True

# --- Interacción con la IA ---

def get_ai_response(user_message):
    """Envía el mensaje del usuario y el contexto de datos a Gemini y obtiene una respuesta."""
    full_prompt = user_message

    # Añadir contexto de datos si está disponible
    data_context = ""
    if st.session_state.excel_data is not None:
        data_context += "\n\nDatos de Excel cargados (primeras 5 filas):\n"
        data_context += st.session_state.excel_data.head().to_markdown(index=False)
        data_context += "\n\n"
    
    if st.session_state.google_sheet_url is not None:
        data_context += f"\n\nEl usuario ha vinculado la siguiente URL de Google Sheet: {st.session_state.google_sheet_url}. "
        data_context += "Considera que esta es una fuente de datos adicional." # Aquí podrías añadir un resumen de los datos si los hubieras cargado realmente

    if data_context:
        full_prompt = f"El siguiente contexto de datos está disponible (si es relevante):{data_context}\n\nConsulta del usuario: {user_message}"

    try:
        # Preparar el historial para Gemini
        gemini_chat_history = []
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                gemini_chat_history.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "ai":
                gemini_chat_history.append({"role": "model", "parts": [{"text": msg["content"]}]})
        
        # Añadir el mensaje actual del usuario al historial para la llamada
        gemini_chat_history.append({"role": "user", "parts": [{"text": full_prompt}]})

        # Usar el modelo de chat para mantener el contexto
        chat = model.start_chat(history=gemini_chat_history[:-1]) # No incluir el último mensaje del usuario en el historial inicial del chat
        response = chat.send_message(full_prompt)
        
        return response.text
    except Exception as e:
        st.error(f"Error al obtener respuesta de la IA: {e}")
        return "Lo siento, no pude generar una respuesta. Por favor, inténtalo de nuevo."

# --- Diseño de la aplicación Streamlit ---

st.title("💰 Asesor Financiero con IA")

# Contenedor principal con dos columnas
col1, col2 = st.columns([0.7, 0.3]) # Chat más grande que la barra lateral de datos

with col2: # Columna derecha para carga de datos
    st.header("Cargar Datos Financieros")

    st.subheader("Archivo Excel (.xlsx, .xls)")
    uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"], key="excel_uploader")
    if uploaded_file is not None:
        if st.button("Procesar Excel"):
            with st.spinner("Procesando archivo Excel..."):
                process_excel_file(uploaded_file)
    
    if st.session_state.excel_data is not None:
        st.success(f"Excel cargado: {uploaded_file.name}")
        st.dataframe(st.session_state.excel_data.head()) # Mostrar las primeras filas

    st.markdown("---")

    st.subheader("Vincular Google Sheet (URL)")
    google_sheet_input = st.text_input("Introduce la URL de tu Google Sheet", key="google_sheet_url_input")
    if st.button("Vincular Hoja"):
        with st.spinner("Vinculando Google Sheet..."):
            process_google_sheet_url(google_sheet_input)
    
    if st.session_state.google_sheet_url is not None:
        st.success(f"Google Sheet vinculado: {st.session_state.google_sheet_url}")
        st.info("Nota: La integración real de Google Sheets requeriría autenticación.")

    st.markdown("---")

    if st.button("Reiniciar Datos Cargados", help="Borra los datos de Excel y la URL de Google Sheet de la sesión."):
        st.session_state.excel_data = None
        st.session_state.google_sheet_url = None
        st.session_state.chat_history.append({"role": "system", "content": "Datos de carga reiniciados."})
        st.experimental_rerun() # Forzar un re-render para limpiar los widgets

with col1: # Columna izquierda para el chat
    st.header("Chat con tu Asesor AI")

    # Área de visualización del chat
    chat_placeholder = st.container()
    with chat_placeholder:
        if not st.session_state.chat_history:
            st.markdown("""
                <div class="chat-message-system">
                    ¡Hola! Soy tu Asesor Financiero AI. ¿En qué puedo ayudarte hoy con tus finanzas?
                    <br/>
                    Puedes empezar preguntando sobre inversiones, presupuestos o cargando tus datos en la sección de la derecha.
                </div>
            """, unsafe_allow_html=True)
        
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message-user">{message["content"]}</div>', unsafe_allow_html=True)
            elif message["role"] == "ai":
                st.markdown(f'<div class="chat-message-ai">{message["content"]}</div>', unsafe_allow_html=True)
            elif message["role"] == "system":
                st.markdown(f'<div class="chat-message-system">{message["content"]}</div>', unsafe_allow_html=True)
    
    # Entrada de texto para el chat
    user_input = st.chat_input("Escribe tu pregunta o comentario...", key="user_input_chat")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Pensando..."):
            ai_response = get_ai_response(user_input)
            st.session_state.chat_history.append({"role": "ai", "content": ai_response})
        st.experimental_rerun() # Forzar un re-render para mostrar el nuevo mensaje

import streamlit as st
import pandas as pd
import google.generativeai as genai
import io # Para manejar archivos en memoria
import json # Para manejar la salida de las funciones
import sys # Para depuración: sys.path
import os # Para depuración: os.getcwd()

# --- Diagnóstico de la versión de google-generativeai y entorno ---
# Esta sección es CRUCIAL para entender por qué @genai.tool podría fallar.
try:
    import pkg_resources
    genai_version = pkg_resources.get_distribution("google-generativeai").version
    st.sidebar.info(f"Versión de google-generativeai cargada: {genai_version}")
    if genai_version < '0.6.0':
        st.sidebar.warning("¡Advertencia! La versión de google-generativeai es anterior a 0.6.0. Por favor, actualiza tu entorno.")
    
    # VERIFICACIÓN EXPLÍCITA DE LA EXISTENCIA DE genai.tool
    if not hasattr(genai, 'tool'):
        st.error("Error CRÍTICO: La funcionalidad de herramientas (@genai.tool) no está disponible en la versión de google-generativeai cargada. "
                 "Esto indica un problema con tu instalación o entorno. Por favor, sigue las instrucciones de reinstalación limpia.")
        st.stop() # Detiene la aplicación si la funcionalidad de herramientas no está presente
        
except Exception as e:
    st.sidebar.error(f"No se pudo verificar la versión de google-generativeai o la funcionalidad de herramientas: {e}")
    st.stop() # Detiene la aplicación si hay un error en el diagnóstico inicial

st.sidebar.subheader("Información de Entorno")
st.sidebar.write(f"Directorio de trabajo actual: `{os.getcwd()}`")
st.sidebar.write("Rutas de búsqueda de módulos (sys.path):")
for path in sys.path:
    st.sidebar.write(f"- `{path}`")


# --- Configuración de Autenticación ---
CORRECT_USERNAME = "javi"
CORRECT_PASSWORD = "javi"

# Configuración de la API de Gemini
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("Error: La clave API de Gemini no está configurada en Streamlit Secrets. "
             "Por favor, añade 'GOOGLE_API_KEY' a tu archivo .streamlit/secrets.toml "
             "o configúrala en el panel de control de Streamlit Cloud.")
    st.stop() # Detiene la ejecución de la aplicación si la clave no está disponible

genai.configure(api_key=API_KEY)

# Inicializar el modelo de Gemini (ahora con herramientas)
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

# --- Herramientas para la IA (Function Calling) ---

@genai.tool
def consultar_datos_tabla(
    query_type: str,
    column_name: str = None,
    filter_column: str = None,
    filter_value: str = None,
    value_column: str = None,
    group_by_column: str = None
) -> str:
    """
    Realiza operaciones de consulta y cálculo sobre la planilla de datos cargada.
    
    Args:
        query_type (str): El tipo de consulta a realizar.
                          Valores posibles: "sum", "average", "count", "unique", "percentage", "filter_sum", "filter_average", "filter_count", "group_by_sum", "group_by_count", "group_by_average".
        column_name (str, opcional): El nombre de la columna sobre la que operar. Requerido para "sum", "average", "count", "unique".
        filter_column (str, opcional): El nombre de la columna para aplicar un filtro. Requerido para "filter_sum", "filter_average", "filter_count".
        filter_value (str, opcional): El valor por el que filtrar en 'filter_column'. Requerido para "filter_sum", "filter_average", "filter_count".
        value_column (str, opcional): El nombre de la columna para sumar/promediar después de filtrar. Requerido para "filter_sum", "filter_average".
        group_by_column (str, opcional): El nombre de la columna para agrupar. Requerido para "group_by_sum", "group_by_count", "group_by_average".
    
    Returns:
        str: Un JSON string con el resultado de la consulta o un mensaje de error.
    """
    df = st.session_state.excel_data
    if df is None:
        return json.dumps({"error": "No hay datos de Excel cargados para consultar."})

    # Convertir nombres de columnas a minúsculas para una coincidencia flexible
    df.columns = df.columns.str.strip() # Limpiar espacios en blanco
    df.columns = df.columns.str.lower()
    
    # Asegurarse de que los nombres de columnas en los argumentos también sean minúsculas
    if column_name: column_name = column_name.lower()
    if filter_column: filter_column = filter_column.lower()
    if filter_value: filter_value = str(filter_value).lower() # Convertir filter_value a string y minúsculas
    if value_column: value_column = value_column.lower()
    if group_by_column: group_by_column = group_by_column.lower()

    # Validar que las columnas existan
    if column_name and column_name not in df.columns:
        return json.dumps({"error": f"Columna '{column_name}' no encontrada en los datos. Columnas disponibles: {list(df.columns)}"})
    if filter_column and filter_column not in df.columns:
        return json.dumps({"error": f"Columna de filtro '{filter_column}' no encontrada en los datos. Columnas disponibles: {list(df.columns)}"})
    if value_column and value_column not in df.columns:
        return json.dumps({"error": f"Columna de valor '{value_column}' no encontrada en los datos. Columnas disponibles: {list(df.columns)}"})
    if group_by_column and group_by_column not in df.columns:
        return json.dumps({"error": f"Columna de agrupación '{group_by_column}' no encontrada en los datos. Columnas disponibles: {list(df.columns)}"})


    try:
        if query_type == "sum":
            result = df[column_name].sum()
            return json.dumps({"result": result, "unit": "sum"})
        elif query_type == "average":
            result = df[column_name].mean()
            return json.dumps({"result": result, "unit": "average"})
        elif query_type == "count":
            result = df[column_name].count()
            return json.dumps({"result": result, "unit": "count"})
        elif query_type == "unique":
            result = df[column_name].nunique()
            return json.dumps({"result": result, "unit": "unique_count"})
        elif query_type == "filter_sum":
            # Asegurarse de que el tipo de datos de la columna de filtro coincida
            if filter_column and filter_column in df.columns:
                # Intentar convertir el valor de filtro al tipo de la columna
                col_dtype = df[filter_column].dtype
                try:
                    if pd.api.types.is_numeric_dtype(col_dtype):
                        filter_value_typed = float(filter_value)
                    elif pd.api.types.is_bool_dtype(col_dtype):
                        filter_value_typed = filter_value.lower() == 'true'
                    else: # Tratar como string por defecto
                        filter_value_typed = filter_value
                except ValueError:
                    return json.dumps({"error": f"No se pudo convertir el valor de filtro '{filter_value}' al tipo de la columna '{filter_column}' ({col_dtype})."})

                filtered_df = df[df[filter_column].astype(str).str.lower() == str(filter_value_typed).lower()]
                result = filtered_df[value_column].sum()
                return json.dumps({"result": result, "unit": "sum", "filter": {filter_column: filter_value}})
            else:
                return json.dumps({"error": "Faltan parámetros para 'filter_sum'."})
        elif query_type == "filter_average":
            if filter_column and filter_column in df.columns:
                col_dtype = df[filter_column].dtype
                try:
                    if pd.api.types.is_numeric_dtype(col_dtype):
                        filter_value_typed = float(filter_value)
                    elif pd.api.types.is_bool_dtype(col_dtype):
                        filter_value_typed = filter_value.lower() == 'true'
                    else:
                        filter_value_typed = filter_value
                except ValueError:
                    return json.dumps({"error": f"No se pudo convertir el valor de filtro '{filter_value}' al tipo de la columna '{filter_column}' ({col_dtype})."})

                filtered_df = df[df[filter_column].astype(str).str.lower() == str(filter_value_typed).lower()]
                result = filtered_df[value_column].mean()
                return json.dumps({"result": result, "unit": "average", "filter": {filter_column: filter_value}})
            else:
                return json.dumps({"error": "Faltan parámetros para 'filter_average'."})
        elif query_type == "filter_count":
            if filter_column and filter_column in df.columns:
                col_dtype = df[filter_column].dtype
                try:
                    if pd.api.types.is_numeric_dtype(col_dtype):
                        filter_value_typed = float(filter_value)
                    elif pd.api.types.is_bool_dtype(col_dtype):
                        filter_value_typed = filter_value.lower() == 'true'
                    else:
                        filter_value_typed = filter_value
                except ValueError:
                    return json.dumps({"error": f"No se pudo convertir el valor de filtro '{filter_value}' al tipo de la columna '{filter_column}' ({col_dtype})."})

                filtered_df = df[df[filter_column].astype(str).str.lower() == str(filter_value_typed).lower()]
                result = len(filtered_df) # Conteo de filas que cumplen el filtro
                return json.dumps({"result": result, "unit": "count", "filter": {filter_column: filter_value}})
            else:
                return json.dumps({"error": "Faltan parámetros para 'filter_count'."})
        elif query_type == "percentage":
            if filter_column and value_column:
                # Asegurarse de que el tipo de datos de la columna de filtro coincida
                if filter_column and filter_column in df.columns:
                    col_dtype = df[filter_column].dtype
                    try:
                        if pd.api.types.is_numeric_dtype(col_dtype):
                            filter_value_typed = float(filter_value)
                        elif pd.api.types.is_bool_dtype(col_dtype):
                            filter_value_typed = filter_value.lower() == 'true'
                        else:
                            filter_value_typed = filter_value
                    except ValueError:
                        return json.dumps({"error": f"No se pudo convertir el valor de filtro '{filter_value}' al tipo de la columna '{filter_column}' ({col_dtype})."})

                total_value = df[value_column].sum()
                filtered_df = df[df[filter_column].astype(str).str.lower() == str(filter_value_typed).lower()]
                filtered_value = filtered_df[value_column].sum()
                if total_value == 0:
                    return json.dumps({"result": 0, "unit": "percentage", "details": "El monto total es cero, por lo que el porcentaje es 0%."})
                percentage = (filtered_value / total_value) * 100
                return json.dumps({"result": percentage, "unit": "percentage", "filter": {filter_column: filter_value}})
            else:
                 return json.dumps({"error": "Para 'percentage', se requieren 'filter_column', 'filter_value' y 'value_column'."})
        elif query_type == "group_by_sum":
            grouped_result = df.groupby(group_by_column)[value_column].sum().to_dict()
            return json.dumps({"result": grouped_result, "unit": "group_by_sum", "group_by": group_by_column})
        elif query_type == "group_by_count":
            grouped_result = df.groupby(group_by_column)[value_column].count().to_dict()
            return json.dumps({"result": grouped_result, "unit": "group_by_count", "group_by": group_by_column})
        elif query_type == "group_by_average":
            grouped_result = df.groupby(group_by_column)[value_column].mean().to_dict()
            return json.dumps({"result": grouped_result, "unit": "group_by_average", "group_by": group_by_column})
        else:
            return json.dumps({"error": f"Tipo de consulta '{query_type}' no soportado."})
    except KeyError as e:
        return json.dumps({"error": f"Columna no encontrada: {e}. Por favor, verifica los nombres de las columnas en tu planilla. Columnas disponibles: {list(df.columns)}"})
    except Exception as e:
        return json.dumps({"error": f"Error al ejecutar la consulta: {e}. Detalles: {sys.exc_info()[0].__name__}"})


# --- Interacción con la IA ---

def get_ai_response(user_message):
    """Envía el mensaje del usuario y el contexto de datos a Gemini y obtiene una respuesta."""
    # La clave API ya se verifica al inicio de la aplicación
    
    # Prepara el historial para Gemini, incluyendo el contexto de la planilla
    gemini_chat_history = []
    
    # Añadir contexto de datos si está disponible
    data_context = ""
    if st.session_state.excel_data is not None:
        buffer = io.StringIO()
        st.session_state.excel_data.info(buf=buffer, verbose=True)
        data_info = buffer.getvalue()

        data_context += "\n\nEl usuario ha cargado una planilla Excel. Aquí tienes un resumen de su estructura y una muestra de sus datos:\n"
        data_context += "--- Información de la Planilla (Columnas y Tipos de Datos) ---\n"
        data_context += data_info
        data_context += "\n--- Primeras 5 filas ---\n"
        data_context += st.session_state.excel_data.head().to_markdown(index=False)
        data_context += "\n--- Últimas 5 filas ---\n"
        data_context += st.session_state.excel_data.tail().to_markdown(index=False)
        data_context += "\n\n"
        data_context += "Eres un Gerente General IA. Tu objetivo es ayudar al usuario a consultar información, hacer cálculos y dar recomendaciones estratégicas sobre su negocio, basándote en esta planilla. "
        data_context += "Tienes acceso a una herramienta llamada `consultar_datos_tabla` que te permite realizar operaciones directas sobre los datos de la planilla. "
        data_context += "Cuando el usuario te pida un cálculo específico, un resumen de datos, o cualquier consulta que pueda resolverse con la planilla, **DEBES utilizar la herramienta `consultar_datos_tabla` para obtener la respuesta numérica o el dato exacto, y luego formular una respuesta clara y directa en lenguaje natural, actuando como un asesor.** "
        data_context += "No debes pedir al usuario que ejecute código Python. Si la herramienta no puede responder, indica claramente el motivo. "
        data_context += "También puedes responder preguntas conceptuales y dar recomendaciones estratégicas que no requieran cálculos directos, basándote en la estructura de los datos y en tu conocimiento general de negocio (finanzas, marketing, operaciones, RRHH, etc.).\n"
        data_context += "Por favor, sé específico en tus preguntas sobre los datos y espera una respuesta directa."

    if st.session_state.google_sheet_url is not None:
        data_context += f"\n\nEl usuario ha vinculado la siguiente URL de Google Sheet: {st.session_state.google_sheet_url}. "
        data_context += "Considera que esta es una fuente de datos adicional, pero las herramientas solo operan sobre la planilla Excel actualmente."

    # Añadir el contexto de datos como un mensaje del sistema al inicio del chat
    if data_context:
        gemini_chat_history.append({"role": "user", "parts": [{"text": data_context}]})
        gemini_chat_history.append({"role": "model", "parts": [{"text": "Entendido. Estoy listo para ayudarte con tus datos."}]}) # Confirmación de la IA

    # Añadir el historial de chat existente (limitado)
    recent_history = st.session_state.chat_history[-10:] # Limitar para evitar exceder el límite de tokens
    for msg in recent_history:
        if msg["role"] == "user":
            gemini_chat_history.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "ai":
            gemini_chat_history.append({"role": "model", "parts": [{"text": msg["content"]}]})

    # Iniciar el chat con el historial y las herramientas
    chat = model.start_chat(history=gemini_chat_history, tools=[consultar_datos_tabla])
    
    try:
        # Enviar el mensaje del usuario
        response = chat.send_message(user_message)

        # Verificar si el modelo ha llamado a una función
        if response.candidates and response.candidates[0].function_calls:
            function_call = response.candidates[0].function_calls[0]
            function_name = function_call.name
            function_args = {k: v for k, v in function_call.args.items()} # Convertir a dict
            
            st.info(f"Gerente General IA está ejecutando una función: {function_name} con argumentos {function_args}")

            # Ejecutar la función Python correspondiente
            if function_name == "consultar_datos_tabla":
                tool_output = consultar_datos_tabla(**function_args)
                
                # Enviar el resultado de la función de vuelta al modelo
                response_after_tool = chat.send_message(
                    genai.types.ToolOutput(tool_code=tool_output) # Usar ToolOutput
                )
                return response_after_tool.text
            else:
                return "La IA intentó usar una función desconocida."
        elif response.text:
            return response.text
        else:
            return "Lo siento, la IA no pudo generar una respuesta significativa."
    except genai.types.BlockedPromptException as e:
        st.error(f"Error de seguridad: La consulta fue bloqueada por las políticas de seguridad de la IA. Por favor, reformula tu pregunta. Detalles: {e}")
        return "Lo siento, tu consulta fue bloqueada por razones de seguridad. Por favor, intenta con una pregunta diferente."
    except Exception as e:
        st.error(f"Error al obtener respuesta de la IA: {e}")
        return "Hubo un error al conectar con la IA o al procesar la consulta. Por favor, inténtalo de nuevo."

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
                Puedes preguntarme sobre finanzas, marketing, operaciones, recursos humanos y más, basándote en los datos que cargues.
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
    st.caption("El modelo de IA ahora puede realizar cálculos directos sobre esta planilla utilizando herramientas internas.")

if st.session_state.google_sheet_url is not None:
    st.subheader("Detalles de Google Sheet Vinculado")
    st.success(f"Google Sheet vinculado: {st.session_state.google_sheet_url}")
    st.info("Nota: La integración real de Google Sheets requeriría autenticación.")

# --- Registro de Preguntas del Usuario (Nuevo) ---
st.subheader("Historial de Preguntas")
if any(msg["role"] == "user" for msg in st.session_state.chat_history):
    # Filtrar solo los mensajes del usuario para el historial
    user_questions = [msg["content"] for msg in st.session_state.chat_history if msg["role"] == "user"]
    for i, question in enumerate(user_questions):
        st.markdown(f"- **Pregunta {i+1}:** {question}")
else:
    st.info("Aún no has realizado ninguna pregunta.")

import unittest
from unittest.mock import MagicMock, patch
import sys

# Simulamos streamlit antes de importar dashboard
mock_st = MagicMock()
sys.modules["streamlit"] = mock_st

# Simulamos supabase para que no intente conectar de verdad
sys.modules["supabase"] = MagicMock()

# Ahora sí importamos dashboard
import dashboard

class TestDashboardAuth(unittest.TestCase):

    def setUp(self):
        """Configuración previa a cada test"""
        # Reseteamos los mocks
        mock_st.reset_mock()
        
        # Simulamos st.secrets
        mock_st.secrets = {"passwords": {"admin": "12345", "paco": "biologo"}}
        
        # Simulamos st.session_state como un diccionario real
        self.mock_session_state = {}
        mock_st.session_state = self.mock_session_state
        
        # Simulamos las columnas (para que 'with col2' funcione)
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        # Hacemos que los contextos 'with' devuelvan el mock de la columna
        mock_col1.__enter__.return_value = mock_col1
        mock_col2.__enter__.return_value = mock_col2

    def test_login_fallido_usuario_incorrecto(self):
        """Prueba que un usuario no registrado no pueda entrar"""
        # Simulamos inputs: Usuario incorrecto, Clave cualquiera
        mock_st.text_input.side_effect = ["hacker", "12345"]
        # Simulamos click en el botón
        mock_st.button.return_value = True
        
        resultado = dashboard.check_password()
        
        # Debe retornar False y mostrar error
        self.assertFalse(resultado)
        mock_st.error.assert_called_once()
        self.assertFalse(self.mock_session_state.get("password_correct", False))

    def test_login_fallido_clave_incorrecta(self):
        """Prueba que la clave incorrecta no permita entrar"""
        # Simulamos inputs: Usuario correcto, Clave MAL
        mock_st.text_input.side_effect = ["admin", "mal"]
        mock_st.button.return_value = True
        
        resultado = dashboard.check_password()
        
        self.assertFalse(resultado)
        mock_st.error.assert_called_once()
    
    def test_login_exitoso(self):
        """Prueba el flujo de éxito (cambio de estado y rerun)"""
        # Simulamos inputs: Usuario correcto, Clave CORRECTA
        mock_st.text_input.side_effect = ["admin", "12345"]
        mock_st.button.return_value = True
        
        # Ejecutamos
        dashboard.check_password()
        
        # VERIFICACIÓN CORREGIDA (Gracias a tu análisis):
        # 1. No verificamos el retorno (porque st.rerun es mock y sigue hasta return False)
        # 2. Verificamos que el ESTADO cambió a True
        self.assertTrue(self.mock_session_state["password_correct"], 
                       "El estado 'password_correct' debería ser True tras login exitoso")
        
        # 3. Verificamos que se llamó a rerun() para recargar la app
        mock_st.rerun.assert_called_once()
        
        # 4. Verificamos mensaje de éxito
        mock_st.success.assert_called()

    def test_sesion_ya_iniciada(self):
        """Si ya está logueado, debe retornar True directo"""
        # Pre-condición: Ya estamos logueados
        self.mock_session_state["password_correct"] = True
        
        resultado = dashboard.check_password()
        
        # Aquí sí debe retornar True directamente
        self.assertTrue(resultado)
        # No debe pedir inputs de nuevo
        mock_st.text_input.assert_not_called()

if __name__ == "__main__":
    unittest.main()
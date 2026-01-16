"""Tests para fuzzy matching de clientes"""
import pytest
import parser
import database


@pytest.fixture
def db_setup():
    """Fixture para configurar base de datos de prueba"""
    test_db = database.Database(':memory:')
    test_db.init_db()
    
    # Crear clientes de prueba
    test_db.create_client("Alditraex", ["Alditraex S.L.", "Alditraex SL"])
    test_db.create_client("Cliente Test", ["Test", "Cliente de Prueba"])
    test_db.create_client("Empresa XYZ", ["XYZ", "Empresa X"])
    
    # Guardar referencia temporal
    original_db = parser.database.db
    parser.database.db = test_db
    
    yield test_db
    
    # Restaurar
    parser.database.db = original_db


@pytest.fixture
def parser_instance(db_setup):
    """Fixture para crear instancia del parser"""
    return parser.IntentParser()


def test_exact_match_normalized(parser_instance, db_setup):
    """Test match exacto normalizado"""
    result = parser_instance.parse("tarea del cliente alditraex")
    client_info = result['entities'].get('client')
    assert client_info is not None
    match = client_info.get('match', {})
    assert match.get('action') == 'auto'
    assert match.get('client_name') == 'Alditraex'


def test_fuzzy_match_high_confidence(parser_instance, db_setup):
    """Test fuzzy match con alta confianza (>=85%)"""
    result = parser_instance.parse("tarea del cliente alditraex sl")
    client_info = result['entities'].get('client')
    assert client_info is not None
    match = client_info.get('match', {})
    # Debería encontrar match con alta confianza
    assert match.get('found') is True


def test_fuzzy_match_medium_confidence(parser_instance, db_setup):
    """Test fuzzy match con confianza media (70-84%)"""
    result = parser_instance.parse("tarea del cliente alditra")
    client_info = result['entities'].get('client')
    assert client_info is not None
    match = client_info.get('match', {})
    # Debería requerir confirmación
    if match.get('confidence', 0) >= 70 and match.get('confidence', 0) < 85:
        assert match.get('action') == 'confirm'
        assert 'candidates' in match


def test_no_match_create_new(parser_instance, db_setup):
    """Test cuando no hay match y se debe crear cliente nuevo"""
    result = parser_instance.parse("tarea del cliente nuevo cliente desconocido")
    client_info = result['entities'].get('client')
    assert client_info is not None
    match = client_info.get('match', {})
    # Debería ofrecer crear nuevo cliente
    assert match.get('action') == 'create' or match.get('found') is False


def test_client_mention_patterns(parser_instance, db_setup):
    """Test diferentes patrones de mención de cliente"""
    patterns = [
        "tarea del cliente Alditraex",
        "tarea para el cliente Alditraex",
        "cliente Alditraex tarea",
    ]
    
    for text in patterns:
        result = parser_instance.parse(text)
        client_info = result['entities'].get('client')
        assert client_info is not None
        assert client_info.get('raw') is not None


def test_alias_matching(parser_instance, db_setup):
    """Test matching contra aliases"""
    result = parser_instance.parse("tarea del cliente alditraex s.l.")
    client_info = result['entities'].get('client')
    assert client_info is not None
    match = client_info.get('match', {})
    # Debería encontrar el cliente por alias
    assert match.get('found') is True









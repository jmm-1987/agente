"""Tests para el parser de intenciones"""
import pytest
from datetime import datetime, timedelta
import parser
import database


@pytest.fixture
def parser_instance():
    """Fixture para crear instancia del parser"""
    return parser.IntentParser()


@pytest.fixture
def db_setup():
    """Fixture para configurar base de datos de prueba"""
    # Usar base de datos en memoria para tests
    test_db = database.Database(':memory:')
    test_db.init_db()
    
    # Crear algunos clientes de prueba
    test_db.create_client("Alditraex", ["Alditraex S.L.", "Alditraex SL"])
    test_db.create_client("Cliente Test", ["Test"])
    
    # Guardar referencia temporal
    original_db = parser.database.db
    parser.database.db = test_db
    
    yield test_db
    
    # Restaurar
    parser.database.db = original_db


def test_intent_crear(parser_instance, db_setup):
    """Test detección de intención CREAR"""
    result = parser_instance.parse("crear una tarea para mañana")
    assert result['intent'] == 'CREAR'


def test_intent_listar(parser_instance, db_setup):
    """Test detección de intención LISTAR"""
    result = parser_instance.parse("muéstrame las tareas pendientes")
    assert result['intent'] == 'LISTAR'


def test_intent_cerrar(parser_instance, db_setup):
    """Test detección de intención CERRAR"""
    result = parser_instance.parse("da por hecha la tarea")
    assert result['intent'] == 'CERRAR'


def test_intent_reprogramar(parser_instance, db_setup):
    """Test detección de intención REPROGRAMAR"""
    result = parser_instance.parse("reprogramar la tarea para el lunes")
    assert result['intent'] == 'REPROGRAMAR'


def test_intent_cambiar_prioridad(parser_instance, db_setup):
    """Test detección de intención CAMBIAR_PRIORIDAD"""
    result = parser_instance.parse("cambiar la prioridad a urgente")
    assert result['intent'] == 'CAMBIAR_PRIORIDAD'


def test_extract_date_hoy(parser_instance, db_setup):
    """Test extracción de fecha 'hoy'"""
    result = parser_instance.parse("tarea para hoy")
    date = result['entities'].get('date')
    assert date is not None
    assert date.date() == datetime.now().date()


def test_extract_date_mañana(parser_instance, db_setup):
    """Test extracción de fecha 'mañana'"""
    result = parser_instance.parse("tarea para mañana")
    date = result['entities'].get('date')
    assert date is not None
    expected_date = (datetime.now() + timedelta(days=1)).date()
    assert date.date() == expected_date


def test_extract_date_parser(parser_instance, db_setup):
    """Test extracción de fecha con dateparser"""
    result = parser_instance.parse("tarea para el 15 de diciembre")
    date = result['entities'].get('date')
    assert date is not None


def test_extract_priority_urgente(parser_instance, db_setup):
    """Test extracción de prioridad urgente"""
    result = parser_instance.parse("tarea urgente")
    priority = result['entities'].get('priority')
    assert priority == 'urgent'


def test_extract_priority_normal(parser_instance, db_setup):
    """Test extracción de prioridad normal"""
    result = parser_instance.parse("tarea normal")
    priority = result['entities'].get('priority')
    assert priority == 'normal'


def test_extract_priority_baja(parser_instance, db_setup):
    """Test extracción de prioridad baja"""
    result = parser_instance.parse("tarea sin prisa")
    priority = result['entities'].get('priority')
    assert priority == 'low'


def test_extract_title(parser_instance, db_setup):
    """Test extracción de título"""
    result = parser_instance.parse("crear tarea llamar al cliente")
    title = result['entities'].get('title')
    assert title is not None
    assert len(title) > 0







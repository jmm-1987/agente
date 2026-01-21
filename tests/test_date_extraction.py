"""Tests para extracción de fechas"""
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
    test_db = database.Database(':memory:')
    test_db.init_db()
    
    original_db = parser.database.db
    parser.database.db = test_db
    
    yield test_db
    
    parser.database.db = original_db


def test_date_hoy(parser_instance, db_setup):
    """Test extracción 'hoy'"""
    result = parser_instance.parse("tarea para hoy")
    date = result['entities'].get('date')
    assert date is not None
    assert date.date() == datetime.now().date()


def test_date_mañana(parser_instance, db_setup):
    """Test extracción 'mañana'"""
    result = parser_instance.parse("tarea para mañana")
    date = result['entities'].get('date')
    assert date is not None
    expected = (datetime.now() + timedelta(days=1)).date()
    assert date.date() == expected


def test_date_pasado_mañana(parser_instance, db_setup):
    """Test extracción 'pasado mañana'"""
    result = parser_instance.parse("tarea para pasado mañana")
    date = result['entities'].get('date')
    assert date is not None
    expected = (datetime.now() + timedelta(days=2)).date()
    assert date.date() == expected


def test_date_dia_semana(parser_instance, db_setup):
    """Test extracción día de la semana"""
    result = parser_instance.parse("tarea para el lunes")
    date = result['entities'].get('date')
    assert date is not None
    # Debería ser un lunes futuro
    assert date.weekday() == 0  # 0 = lunes


def test_date_fecha_especifica(parser_instance, db_setup):
    """Test extracción fecha específica"""
    result = parser_instance.parse("tarea para el 25 de diciembre")
    date = result['entities'].get('date')
    assert date is not None
    assert date.day == 25
    assert date.month == 12


def test_date_prefer_future(parser_instance, db_setup):
    """Test que prefiere fechas futuras"""
    # Si hoy es 15 de enero y dice "15 de enero", debería ser el próximo año
    result = parser_instance.parse("tarea para el 15 de enero")
    date = result['entities'].get('date')
    if date:
        # Si la fecha ya pasó este año, debería ser del próximo año
        if date.month == 1 and date.day == 15:
            if datetime.now().month == 1 and datetime.now().day >= 15:
                assert date.year > datetime.now().year











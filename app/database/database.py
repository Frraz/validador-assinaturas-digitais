from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from contextlib import contextmanager

# Configuração de conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signatures.db")

# Criar engine do SQLAlchemy
engine = create_engine(DATABASE_URL)

# Criar factory para sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos declarativos
Base = declarative_base()

@contextmanager
def get_db():
    """
    Contexto para obter sessão do banco de dados
    
    Yields:
        Session: Sessão do SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_or_create(db, model, **kwargs):
    """
    Obtém um objeto ou cria se não existir
    
    Args:
        db: Sessão do SQLAlchemy
        model: Modelo SQLAlchemy
        **kwargs: Filtros para buscar o objeto
        
    Returns:
        Objeto do modelo, boolean indicando se foi criado
    """
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        db.add(instance)
        db.commit()
        return instance, True
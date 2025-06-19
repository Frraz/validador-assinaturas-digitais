from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
import os
import uuid
import shutil
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.validation.signature_validator import validate_signature
from app.report.pdf_generator import generate_report
from app.database.database import get_db, engine
from app.database.models import Base, ValidationJob, ValidationFile, RejectedFile

# Criar tabelas no banco de dados
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Validador de Assinaturas Digitais em Massa")

# Configuração de diretórios
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

# Garantir que os diretórios existam
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Configuração de templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configurações de segurança
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf"}
FILE_RETENTION_DAYS = 7  # Manter arquivos por 7 dias
REPORT_RETENTION_DAYS = 30  # Manter relatórios por 30 dias


@app.on_event("startup")
async def setup_periodic_tasks():
    """Configure tarefas periódicas ao iniciar o aplicativo"""
    asyncio.create_task(clean_old_files_periodically())


async def clean_old_files_periodically():
    """Remove arquivos temporários antigos a cada 24 horas"""
    while True:
        await asyncio.sleep(86400)  # 24 horas
        
        # Limpar arquivos de upload antigos (>7 dias)
        clean_old_directories(UPLOAD_DIR, max_age_days=FILE_RETENTION_DAYS)
        
        # Limpar relatórios antigos (>30 dias)
        clean_old_directories(REPORT_DIR, max_age_days=REPORT_RETENTION_DAYS)
        
        # Remover jobs expirados do banco de dados
        clean_expired_jobs_from_db()


def clean_old_directories(directory_path: str, max_age_days: int):
    """
    Remove arquivos e diretórios mais antigos que max_age_days
    
    Args:
        directory_path: Caminho do diretório a ser limpo
        max_age_days: Idade máxima em dias para manter arquivos
    """
    now = datetime.now()
    cutoff_date = now - timedelta(days=max_age_days)
    
    try:
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            
            # Obter a data de modificação
            mtime = os.path.getmtime(item_path)
            mod_date = datetime.fromtimestamp(mtime)
            
            # Verificar se é mais antigo que o limite
            if mod_date < cutoff_date:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    os.remove(item_path)
                print(f"Removido {item_path} (modificado em {mod_date})")
    except Exception as e:
        print(f"Erro ao limpar diretório {directory_path}: {e}")


def clean_expired_jobs_from_db():
    """Remove jobs expirados do banco de dados"""
    try:
        with get_db() as db:
            cutoff_date = datetime.now() - timedelta(days=FILE_RETENTION_DAYS)
            expired_jobs = db.query(ValidationJob).filter(ValidationJob.created_at < cutoff_date).all()
            
            for job in expired_jobs:
                # Remover diretório de upload se existir
                job_dir = os.path.join(UPLOAD_DIR, job.id)
                if os.path.exists(job_dir):
                    try:
                        shutil.rmtree(job_dir)
                    except Exception as e:
                        print(f"Erro ao remover diretório {job_dir}: {e}")
                
                # Remover relatório se existir
                if job.report_path and os.path.exists(job.report_path):
                    try:
                        os.remove(job.report_path)
                    except Exception as e:
                        print(f"Erro ao remover relatório {job.report_path}: {e}")
                
                # Remover do banco de dados
                db.delete(job)
            
            db.commit()
            print(f"Removidos {len(expired_jobs)} jobs expirados do banco de dados")
    except Exception as e:
        print(f"Erro ao limpar jobs expirados do banco de dados: {e}")


def validate_file_security(file: UploadFile) -> str:
    """
    Valida a segurança de um arquivo enviado
    
    Args:
        file: Arquivo enviado
        
    Returns:
        str: Mensagem de erro se o arquivo não é seguro, None caso contrário
    """
    # Verificar extensão do arquivo
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return f"Tipo de arquivo não permitido: {ext}. Apenas PDF é aceito."
    
    # Verificar tamanho do arquivo (streaming para não carregar tudo na memória)
    content = file.file.read(MAX_FILE_SIZE + 1)
    file_size = len(content)
    
    # Retornar o ponteiro do arquivo para o início
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return f"Arquivo muito grande: {file.filename}. Máximo permitido: {MAX_FILE_SIZE/1024/1024:.1f} MB"
    
    # Verificar assinatura de conteúdo para PDF
    if not content.startswith(b'%PDF-'):
        return f"Arquivo não é um PDF válido: {file.filename}"
    
    return None


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload/")
async def upload_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi enviado")
    
    # Criar um ID único para este trabalho de validação
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Criar job no banco de dados
    db_job = ValidationJob(
        id=job_id,
        created_at=datetime.now(),
        status="processando",
        progress=0,
        report_path=None
    )
    db.add(db_job)
    
    # Armazenar os arquivos enviados
    saved_files = []
    rejected_files = []
    
    for file in files:
        # Verificar segurança do arquivo
        security_error = validate_file_security(file)
        if security_error:
            # Adicionar ao banco de dados como arquivo rejeitado
            rejected_file = RejectedFile(
                id=str(uuid.uuid4()),
                job_id=job_id,
                filename=file.filename,
                error=security_error
            )
            db.add(rejected_file)
            rejected_files.append(rejected_file)
            continue
            
        if not file.filename.lower().endswith('.pdf'):
            # Adicionar ao banco de dados como arquivo rejeitado
            rejected_file = RejectedFile(
                id=str(uuid.uuid4()),
                job_id=job_id,
                filename=file.filename,
                error="Tipo de arquivo não permitido. Apenas PDF é aceito."
            )
            db.add(rejected_file)
            rejected_files.append(rejected_file)
            continue
            
        try:
            file_path = os.path.join(job_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Adicionar ao banco de dados como arquivo para validação
            validation_file = ValidationFile(
                id=str(uuid.uuid4()),
                job_id=job_id,
                filename=file.filename,
                path=file_path,
                status="pendente"
            )
            db.add(validation_file)
            saved_files.append(validation_file)
            
        except Exception as e:
            # Adicionar ao banco de dados como arquivo rejeitado
            rejected_file = RejectedFile(
                id=str(uuid.uuid4()),
                job_id=job_id,
                filename=file.filename,
                error=f"Erro ao salvar arquivo: {str(e)}"
            )
            db.add(rejected_file)
            rejected_files.append(rejected_file)
    
    # Commit para salvar as alterações no banco de dados
    db.commit()
    
    # Se nenhum arquivo foi salvo, retornar erro
    if not saved_files:
        # Limpar o diretório vazio
        try:
            os.rmdir(job_dir)
        except:
            pass
        
        # Remover job do banco de dados
        db.delete(db_job)
        db.commit()
        
        error_detail = "Nenhum arquivo PDF válido foi enviado"
        if rejected_files:
            error_detail = f"Arquivos rejeitados: {', '.join(f.filename for f in rejected_files)}"
        raise HTTPException(status_code=400, detail=error_detail)
    
    # Iniciar processo de validação em background
    asyncio.create_task(process_validation_job(job_id))
    
    return {"job_id": job_id, "message": f"{len(saved_files)} arquivos recebidos para validação"}


@app.get("/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    # Buscar job no banco de dados
    job = db.query(ValidationJob).filter(ValidationJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Trabalho de validação não encontrado")
    
    # Converter para dicionário
    return job.to_dict()


@app.get("/report/{job_id}")
async def get_report(job_id: str, db: Session = Depends(get_db)):
    # Buscar job no banco de dados
    job = db.query(ValidationJob).filter(ValidationJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Trabalho de validação não encontrado")
    
    if job.status != "completo" or not job.report_path:
        raise HTTPException(status_code=404, detail="Relatório ainda não disponível")
    
    if not os.path.exists(job.report_path):
        raise HTTPException(status_code=404, detail="Arquivo de relatório não encontrado")
    
    return FileResponse(
        job.report_path,
        filename=f"relatorio_validacao_{job_id}.pdf",
        media_type="application/pdf"
    )


async def process_validation_job(job_id: str):
    """Processa a validação de assinaturas em background"""
    with get_db() as db:
        # Buscar job no banco de dados
        job = db.query(ValidationJob).filter(ValidationJob.id == job_id).first()
        if not job:
            print(f"Job {job_id} não encontrado no banco de dados")
            return
        
        # Buscar arquivos para validação
        files = db.query(ValidationFile).filter(ValidationFile.job_id == job_id).all()
        total_files = len(files)
        
        for i, file in enumerate(files):
            # Atualizar progresso
            progress = int((i / total_files) * 100)
            job.progress = progress
            db.commit()
            
            try:
                # Validar assinatura do documento
                validation_result = validate_signature(file.path)
                
                # Atualizar informações do arquivo
                file.status = "validado"
                file.is_valid = validation_result["valid"]
                file.details = validation_result
                
                if not validation_result["valid"] and "error" in validation_result:
                    file.error = validation_result["error"]
                
            except Exception as e:
                file.status = "erro"
                file.error = str(e)
                file.is_valid = False
            
            # Salvar alterações no banco de dados
            db.commit()
        
        # Gerar relatório PDF com os resultados
        report_file = os.path.join(REPORT_DIR, f"report_{job_id}.pdf")
        
        # Converter objetos SQLAlchemy para dicionários para o gerador de relatório
        files_dict = [file.to_dict() for file in files]
        generate_report(files_dict, report_file)
        
        # Atualizar informações do trabalho
        job.status = "completo"
        job.progress = 100
        job.report_path = report_file
        
        # Salvar alterações no banco de dados
        db.commit()
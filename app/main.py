from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
import os
import uuid
import shutil
import asyncio
from datetime import datetime

from app.validation.signature_validator import validate_signature
from app.report.pdf_generator import generate_report

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

# Armazenamento em memória dos trabalhos de validação
validation_jobs = {}


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi enviado")
    
    # Criar um ID único para este trabalho de validação
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Armazenar os arquivos enviados
    saved_files = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue  # Ignorar arquivos que não sejam PDF por enquanto
            
        file_path = os.path.join(job_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append({
            "filename": file.filename,
            "path": file_path,
            "status": "pendente"
        })
    
    # Inicializar informações do trabalho
    validation_jobs[job_id] = {
        "id": job_id,
        "created_at": datetime.now().isoformat(),
        "status": "processando",
        "files": saved_files,
        "progress": 0,
        "report_path": None
    }
    
    # Iniciar processo de validação em background
    asyncio.create_task(process_validation_job(job_id))
    
    return {"job_id": job_id, "message": f"{len(saved_files)} arquivos recebidos para validação"}


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail="Trabalho de validação não encontrado")
    
    return validation_jobs[job_id]


@app.get("/report/{job_id}")
async def get_report(job_id: str):
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail="Trabalho de validação não encontrado")
    
    job = validation_jobs[job_id]
    if job["status"] != "completo" or not job["report_path"]:
        raise HTTPException(status_code=404, detail="Relatório ainda não disponível")
    
    return FileResponse(
        job["report_path"],
        filename="relatorio_validacao.pdf",
        media_type="application/pdf"
    )


async def process_validation_job(job_id: str):
    """Processa a validação de assinaturas em background"""
    job = validation_jobs[job_id]
    total_files = len(job["files"])
    
    for i, file_info in enumerate(job["files"]):
        # Atualizar progresso
        job["progress"] = int((i / total_files) * 100)
        
        try:
            # Validar assinatura do documento
            validation_result = validate_signature(file_info["path"])
            file_info.update({
                "status": "validado",
                "is_valid": validation_result["valid"],
                "details": validation_result
            })
        except Exception as e:
            file_info.update({
                "status": "erro",
                "error": str(e)
            })
    
    # Gerar relatório PDF com os resultados
    report_file = os.path.join(REPORT_DIR, f"report_{job_id}.pdf")
    generate_report(job["files"], report_file)
    
    # Atualizar informações do trabalho
    job["status"] = "completo"
    job["progress"] = 100
    job["report_path"] = report_file
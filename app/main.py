from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
import os
import uuid
import shutil
import asyncio
import logging
from datetime import datetime

from app.validation.signature_validator import validate_signature
from app.report.pdf_generator import generate_report
from app.utils.cleanup import initialize_cleanup_manager, get_cleanup_manager
from app.utils.pdf_security import validate_pdf_security

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Inicializar o gerenciador de limpeza
cleanup_manager = initialize_cleanup_manager(UPLOAD_DIR, REPORT_DIR, max_age_hours=24)


@app.on_event("startup")
async def startup_event():
    """Evento executado na inicialização da aplicação"""
    logger.info("Iniciando aplicação de validação de assinaturas digitais")
    
    # Iniciar limpeza periódica (a cada 2 horas)
    await cleanup_manager.start_periodic_cleanup(interval_hours=2)
    logger.info("Sistema de limpeza automática iniciado")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento executado no encerramento da aplicação"""
    logger.info("Encerrando aplicação")
    
    # Parar limpeza periódica
    await cleanup_manager.stop_periodic_cleanup()
    logger.info("Sistema de limpeza automática parado")


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
    
    # Armazenar os arquivos enviados com validação de segurança
    saved_files = []
    security_issues = []
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue  # Ignorar arquivos que não sejam PDF
            
        # Salvar arquivo temporariamente
        file_path = os.path.join(job_dir, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Validar segurança do PDF
            security_result = validate_pdf_security(file_path)
            
            file_info = {
                "filename": file.filename,
                "path": file_path,
                "status": "pendente",
                "security_validation": security_result
            }
            
            if not security_result["is_safe"]:
                file_info["status"] = "rejeitado"
                file_info["rejection_reason"] = "Problemas de segurança detectados"
                security_issues.append(f"{file.filename}: {', '.join(security_result['security_issues'])}")
                # Remover arquivo inseguro
                try:
                    os.remove(file_path)
                except:
                    pass
            else:
                # Arquivo aprovado na validação de segurança
                if security_result["warnings"]:
                    file_info["security_warnings"] = security_result["warnings"]
                    
            saved_files.append(file_info)
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file.filename}: {e}")
            security_issues.append(f"{file.filename}: Erro ao processar arquivo")
    
    # Filtrar apenas arquivos aprovados para validação
    approved_files = [f for f in saved_files if f["status"] != "rejeitado"]
    
    if not approved_files:
        # Limpar diretório se nenhum arquivo foi aprovado
        try:
            shutil.rmtree(job_dir)
        except:
            pass
        raise HTTPException(
            status_code=400, 
            detail=f"Nenhum arquivo válido para processar. Problemas: {'; '.join(security_issues)}"
        )
    
    # Inicializar informações do trabalho
    validation_jobs[job_id] = {
        "id": job_id,
        "created_at": datetime.now().isoformat(),
        "status": "processando",
        "files": saved_files,
        "approved_files_count": len(approved_files),
        "rejected_files_count": len(saved_files) - len(approved_files),
        "security_issues": security_issues,
        "progress": 0,
        "report_path": None
    }
    
    # Iniciar processo de validação em background
    asyncio.create_task(process_validation_job(job_id))
    
    message = f"{len(approved_files)} arquivos aprovados para validação"
    if security_issues:
        message += f", {len(security_issues)} arquivos rejeitados por problemas de segurança"
    
    return {"job_id": job_id, "message": message}


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


@app.get("/admin/cleanup")
async def manual_cleanup():
    """Endpoint para executar limpeza manual (apenas para administradores)"""
    try:
        cleanup_result = await cleanup_manager.cleanup_old_files()
        return {
            "success": True,
            "message": "Limpeza manual executada com sucesso",
            "details": cleanup_result
        }
    except Exception as e:
        logger.error(f"Erro na limpeza manual: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na limpeza: {str(e)}")


@app.get("/admin/storage-stats")
async def get_storage_stats():
    """Endpoint para obter estatísticas de armazenamento"""
    try:
        stats = cleanup_manager.get_storage_stats()
        return {
            "success": True,
            "storage_stats": stats
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


@app.delete("/admin/job/{job_id}")
async def cleanup_job(job_id: str):
    """Endpoint para limpar arquivos de um job específico"""
    try:
        success = await cleanup_manager.cleanup_job_files(job_id)
        
        # Remover da memória também
        if job_id in validation_jobs:
            del validation_jobs[job_id]
        
        if success:
            return {"success": True, "message": f"Arquivos do job {job_id} removidos com sucesso"}
        else:
            return {"success": False, "message": f"Erro ao remover arquivos do job {job_id}"}
            
    except Exception as e:
        logger.error(f"Erro ao limpar job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na limpeza: {str(e)}")


async def process_validation_job(job_id: str):
    """Processa a validação de assinaturas em background com limpeza automática"""
    job = validation_jobs[job_id]
    
    # Processar apenas arquivos aprovados
    files_to_process = [f for f in job["files"] if f["status"] != "rejeitado"]
    total_files = len(files_to_process)
    
    if total_files == 0:
        job["status"] = "erro"
        job["error"] = "Nenhum arquivo válido para processar"
        return
    
    try:
        for i, file_info in enumerate(files_to_process):
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
                
                logger.info(f"Arquivo {file_info['filename']} validado: {'válido' if validation_result['valid'] else 'inválido'}")
                
            except Exception as e:
                logger.error(f"Erro ao validar {file_info['filename']}: {e}")
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
        job["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Job {job_id} concluído com sucesso")
        
    except Exception as e:
        logger.error(f"Erro crítico no processamento do job {job_id}: {e}")
        job["status"] = "erro"
        job["error"] = f"Erro crítico: {str(e)}"
    
    finally:
        # Agendar limpeza dos arquivos de upload do job após 1 hora
        asyncio.create_task(delayed_job_cleanup(job_id, delay_hours=1))


async def delayed_job_cleanup(job_id: str, delay_hours: int = 1):
    """Limpa arquivos de um job após um delay especificado"""
    try:
        # Aguardar o delay
        await asyncio.sleep(delay_hours * 3600)
        
        # Verificar se o job ainda existe
        if job_id in validation_jobs:
            job = validation_jobs[job_id]
            
            # Limpar apenas arquivos de upload, manter relatório
            job_upload_dir = os.path.join(UPLOAD_DIR, job_id)
            if os.path.exists(job_upload_dir):
                shutil.rmtree(job_upload_dir)
                logger.info(f"Arquivos de upload do job {job_id} removidos após {delay_hours} horas")
                
                # Atualizar informações dos arquivos
                for file_info in job["files"]:
                    if "path" in file_info:
                        file_info["path"] = "removido"
                        file_info["cleanup_status"] = "arquivos removidos"
                        
    except Exception as e:
        logger.error(f"Erro na limpeza atrasada do job {job_id}: {e}")
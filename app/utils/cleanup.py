"""
Sistema de limpeza automática de arquivos temporários
"""
import os
import shutil
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import glob

logger = logging.getLogger(__name__)


class FileCleanupManager:
    """Gerenciador de limpeza de arquivos temporários"""
    
    def __init__(self, upload_dir: str, report_dir: str, max_age_hours: int = 24):
        self.upload_dir = upload_dir
        self.report_dir = report_dir
        self.max_age_hours = max_age_hours
        self.cleanup_task = None
        
    async def start_periodic_cleanup(self, interval_hours: int = 1):
        """Inicia limpeza periódica automática"""
        logger.info(f"Iniciando limpeza periódica a cada {interval_hours} horas")
        
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_old_files()
                    await asyncio.sleep(interval_hours * 3600)  # Converter horas para segundos
                except asyncio.CancelledError:
                    logger.info("Limpeza periódica cancelada")
                    break
                except Exception as e:
                    logger.error(f"Erro na limpeza periódica: {e}")
                    await asyncio.sleep(300)  # Esperar 5 minutos antes de tentar novamente
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        
    async def stop_periodic_cleanup(self):
        """Para a limpeza periódica"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("Limpeza periódica parada")
    
    async def cleanup_old_files(self) -> dict:
        """Remove arquivos antigos dos diretórios de upload e relatórios"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
        
        result = {
            "uploads_removed": 0,
            "reports_removed": 0,
            "total_space_freed": 0,
            "errors": []
        }
        
        # Limpar diretório de uploads
        try:
            uploads_result = await self._cleanup_directory(self.upload_dir, cutoff_time)
            result["uploads_removed"] = uploads_result["files_removed"]
            result["total_space_freed"] += uploads_result["space_freed"]
            result["errors"].extend(uploads_result["errors"])
        except Exception as e:
            error_msg = f"Erro ao limpar uploads: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        # Limpar diretório de relatórios
        try:
            reports_result = await self._cleanup_directory(self.report_dir, cutoff_time)
            result["reports_removed"] = reports_result["files_removed"]
            result["total_space_freed"] += reports_result["space_freed"]
            result["errors"].extend(reports_result["errors"])
        except Exception as e:
            error_msg = f"Erro ao limpar relatórios: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        if result["uploads_removed"] > 0 or result["reports_removed"] > 0:
            logger.info(f"Limpeza concluída: {result['uploads_removed']} uploads, "
                       f"{result['reports_removed']} relatórios removidos, "
                       f"{result['total_space_freed']} bytes liberados")
        
        return result
    
    async def _cleanup_directory(self, directory: str, cutoff_time: datetime) -> dict:
        """Limpa um diretório específico"""
        result = {
            "files_removed": 0,
            "space_freed": 0,
            "errors": []
        }
        
        if not os.path.exists(directory):
            return result
            
        try:
            for root, dirs, files in os.walk(directory):
                # Limpar arquivos antigos
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Verificar idade do arquivo
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            result["files_removed"] += 1
                            result["space_freed"] += file_size
                            logger.debug(f"Arquivo removido: {file_path}")
                    except Exception as e:
                        error_msg = f"Erro ao remover arquivo {file_path}: {str(e)}"
                        logger.warning(error_msg)
                        result["errors"].append(error_msg)
                
                # Remover diretórios vazios antigos
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if self._is_directory_old_and_empty(dir_path, cutoff_time):
                            shutil.rmtree(dir_path)
                            logger.debug(f"Diretório vazio removido: {dir_path}")
                    except Exception as e:
                        error_msg = f"Erro ao remover diretório {dir_path}: {str(e)}"
                        logger.warning(error_msg)
                        result["errors"].append(error_msg)
                        
        except Exception as e:
            error_msg = f"Erro ao percorrer diretório {directory}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result
    
    def _is_directory_old_and_empty(self, directory: str, cutoff_time: datetime) -> bool:
        """Verifica se um diretório é antigo e vazio"""
        try:
            if not os.path.exists(directory):
                return False
                
            # Verificar se está vazio
            if os.listdir(directory):
                return False
                
            # Verificar idade
            dir_time = datetime.fromtimestamp(os.path.getmtime(directory))
            return dir_time < cutoff_time
            
        except Exception:
            return False
    
    async def cleanup_job_files(self, job_id: str) -> bool:
        """Remove arquivos específicos de um job"""
        try:
            # Remover diretório de upload do job
            job_upload_dir = os.path.join(self.upload_dir, job_id)
            if os.path.exists(job_upload_dir):
                shutil.rmtree(job_upload_dir)
                logger.info(f"Diretório de upload removido: {job_upload_dir}")
            
            # Remover relatório do job
            report_pattern = os.path.join(self.report_dir, f"report_{job_id}*")
            for report_file in glob.glob(report_pattern):
                os.remove(report_file)
                logger.info(f"Relatório removido: {report_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos do job {job_id}: {e}")
            return False
    
    def get_directory_size(self, directory: str) -> int:
        """Calcula o tamanho total de um diretório"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except Exception:
                        continue
        except Exception:
            pass
        return total_size
    
    def get_storage_stats(self) -> dict:
        """Retorna estatísticas de armazenamento"""
        try:
            upload_size = self.get_directory_size(self.upload_dir)
            report_size = self.get_directory_size(self.report_dir)
            
            # Contar arquivos
            upload_files = sum([len(files) for r, d, files in os.walk(self.upload_dir)])
            report_files = sum([len(files) for r, d, files in os.walk(self.report_dir)])
            
            return {
                "upload_directory": {
                    "path": self.upload_dir,
                    "size_bytes": upload_size,
                    "size_mb": round(upload_size / (1024 * 1024), 2),
                    "file_count": upload_files
                },
                "report_directory": {
                    "path": self.report_dir,
                    "size_bytes": report_size,
                    "size_mb": round(report_size / (1024 * 1024), 2),
                    "file_count": report_files
                },
                "total_size_bytes": upload_size + report_size,
                "total_size_mb": round((upload_size + report_size) / (1024 * 1024), 2),
                "max_age_hours": self.max_age_hours
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de armazenamento: {e}")
            return {"error": str(e)}


# Singleton para usar globalmente
cleanup_manager: Optional[FileCleanupManager] = None


def get_cleanup_manager() -> Optional[FileCleanupManager]:
    """Retorna a instância global do gerenciador de limpeza"""
    return cleanup_manager


def initialize_cleanup_manager(upload_dir: str, report_dir: str, max_age_hours: int = 24) -> FileCleanupManager:
    """Inicializa o gerenciador de limpeza global"""
    global cleanup_manager
    cleanup_manager = FileCleanupManager(upload_dir, report_dir, max_age_hours)
    return cleanup_manager
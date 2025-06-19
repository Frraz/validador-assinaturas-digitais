"""
Validador de segurança para arquivos PDF
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from PyPDF2 import PdfReader
import re

logger = logging.getLogger(__name__)


class PDFSecurityValidator:
    """Validador de segurança para arquivos PDF"""
    
    # Padrões suspeitos que podem indicar conteúdo malicioso
    SUSPICIOUS_PATTERNS = [
        # JavaScript
        b'/JS',
        b'/JavaScript',
        b'javascript:',
        
        # Ações automáticas
        b'/OpenAction',
        b'/AA',
        
        # Formulários e campos de entrada
        b'/XFA',
        
        # Anexos e arquivos embarcados
        b'/EmbeddedFile',
        b'/Filespec',
        
        # URIs e links externos
        b'/URI',
        b'http://',
        b'https://',
        b'ftp://',
        
        # Comandos potencialmente perigosos
        b'/Launch',
        b'/SubmitForm',
        b'/ImportData'
    ]
    
    # Tamanho máximo permitido (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # Número máximo de páginas
    MAX_PAGES = 1000
    
    def __init__(self):
        self.last_validation_details = {}
    
    def validate_pdf_security(self, file_path: str) -> Dict:
        """
        Valida a segurança de um arquivo PDF
        
        Args:
            file_path: Caminho para o arquivo PDF
            
        Returns:
            Dicionário com resultado da validação de segurança
        """
        validation_result = {
            "is_safe": True,
            "security_issues": [],
            "warnings": [],
            "file_info": {},
            "validation_details": {}
        }
        
        try:
            # Verificações básicas de arquivo
            basic_checks = self._perform_basic_file_checks(file_path)
            validation_result["file_info"] = basic_checks["file_info"]
            
            if not basic_checks["is_valid"]:
                validation_result["is_safe"] = False
                validation_result["security_issues"].extend(basic_checks["issues"])
                return validation_result
            
            # Verificações de estrutura PDF
            structure_checks = self._perform_structure_checks(file_path)
            validation_result["validation_details"]["structure"] = structure_checks
            
            if not structure_checks["is_valid"]:
                validation_result["is_safe"] = False
                validation_result["security_issues"].extend(structure_checks["issues"])
            
            # Verificações de conteúdo suspeito
            content_checks = self._perform_content_checks(file_path)
            validation_result["validation_details"]["content"] = content_checks
            
            if content_checks["suspicious_patterns_found"]:
                validation_result["warnings"].extend(content_checks["warnings"])
                # Por enquanto, apenas avisos para conteúdo suspeito
                
            # Verificações de metadata
            metadata_checks = self._perform_metadata_checks(file_path)
            validation_result["validation_details"]["metadata"] = metadata_checks
            validation_result["file_info"].update(metadata_checks["metadata"])
            
            if metadata_checks["suspicious_metadata"]:
                validation_result["warnings"].extend(metadata_checks["warnings"])
            
            self.last_validation_details = validation_result["validation_details"]
            
        except Exception as e:
            logger.error(f"Erro na validação de segurança do PDF: {e}")
            validation_result["is_safe"] = False
            validation_result["security_issues"].append(f"Erro na validação: {str(e)}")
        
        return validation_result
    
    def _perform_basic_file_checks(self, file_path: str) -> Dict:
        """Verifica aspectos básicos do arquivo"""
        result = {
            "is_valid": True,
            "issues": [],
            "file_info": {}
        }
        
        try:
            # Verificar se arquivo existe
            if not os.path.exists(file_path):
                result["is_valid"] = False
                result["issues"].append("Arquivo não encontrado")
                return result
            
            # Verificar tamanho do arquivo
            file_size = os.path.getsize(file_path)
            result["file_info"]["size_bytes"] = file_size
            result["file_info"]["size_mb"] = round(file_size / (1024 * 1024), 2)
            
            if file_size > self.MAX_FILE_SIZE:
                result["is_valid"] = False
                result["issues"].append(f"Arquivo muito grande: {result['file_info']['size_mb']}MB (máximo: {self.MAX_FILE_SIZE // (1024*1024)}MB)")
            
            if file_size == 0:
                result["is_valid"] = False
                result["issues"].append("Arquivo está vazio")
                return result
            
            # Verificar cabeçalho PDF
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    result["is_valid"] = False
                    result["issues"].append("Arquivo não possui cabeçalho PDF válido")
                    return result
                
                # Extrair versão PDF
                version_match = re.match(rb'%PDF-(\d+\.\d+)', header)
                if version_match:
                    result["file_info"]["pdf_version"] = version_match.group(1).decode()
            
        except Exception as e:
            result["is_valid"] = False
            result["issues"].append(f"Erro ao verificar arquivo básico: {str(e)}")
        
        return result
    
    def _perform_structure_checks(self, file_path: str) -> Dict:
        """Verifica a estrutura do PDF"""
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "page_count": 0,
            "has_encryption": False,
            "has_forms": False
        }
        
        try:
            with open(file_path, 'rb') as f:
                pdf = PdfReader(f)
                
                # Verificar número de páginas
                result["page_count"] = len(pdf.pages)
                if result["page_count"] > self.MAX_PAGES:
                    result["is_valid"] = False
                    result["issues"].append(f"Muitas páginas: {result['page_count']} (máximo: {self.MAX_PAGES})")
                
                if result["page_count"] == 0:
                    result["is_valid"] = False
                    result["issues"].append("PDF não possui páginas")
                
                # Verificar criptografia
                if pdf.is_encrypted:
                    result["has_encryption"] = True
                    result["warnings"].append("PDF está criptografado")
                
                # Verificar presença de formulários
                if "/Root" in pdf.trailer:
                    root = pdf.trailer["/Root"]
                    if "/AcroForm" in root:
                        result["has_forms"] = True
                        result["warnings"].append("PDF contém formulários interativos")
                
        except Exception as e:
            result["is_valid"] = False
            result["issues"].append(f"Erro ao analisar estrutura do PDF: {str(e)}")
        
        return result
    
    def _perform_content_checks(self, file_path: str) -> Dict:
        """Verifica conteúdo suspeito no PDF"""
        result = {
            "suspicious_patterns_found": False,
            "patterns_detected": [],
            "warnings": []
        }
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                
                # Buscar padrões suspeitos
                for pattern in self.SUSPICIOUS_PATTERNS:
                    if pattern in content:
                        result["suspicious_patterns_found"] = True
                        pattern_str = pattern.decode('utf-8', errors='ignore')
                        result["patterns_detected"].append(pattern_str)
                        
                        # Adicionar avisos específicos
                        if pattern in [b'/JS', b'/JavaScript', b'javascript:']:
                            result["warnings"].append("PDF contém JavaScript")
                        elif pattern in [b'/OpenAction', b'/AA']:
                            result["warnings"].append("PDF contém ações automáticas")
                        elif pattern == b'/XFA':
                            result["warnings"].append("PDF contém formulários XFA")
                        elif pattern in [b'/EmbeddedFile', b'/Filespec']:
                            result["warnings"].append("PDF contém arquivos embarcados")
                        elif pattern in [b'/URI', b'http://', b'https://', b'ftp://']:
                            result["warnings"].append("PDF contém links externos")
                        elif pattern in [b'/Launch', b'/SubmitForm', b'/ImportData']:
                            result["warnings"].append("PDF contém comandos potencialmente perigosos")
                
        except Exception as e:
            logger.error(f"Erro ao verificar conteúdo do PDF: {e}")
            result["warnings"].append(f"Erro na análise de conteúdo: {str(e)}")
        
        return result
    
    def _perform_metadata_checks(self, file_path: str) -> Dict:
        """Verifica metadata do PDF"""
        result = {
            "suspicious_metadata": False,
            "metadata": {},
            "warnings": []
        }
        
        try:
            with open(file_path, 'rb') as f:
                pdf = PdfReader(f)
                
                # Extrair metadata
                if pdf.metadata:
                    metadata = pdf.metadata
                    
                    # Extrair informações básicas
                    result["metadata"] = {
                        "title": str(metadata.get("/Title", "")) if "/Title" in metadata else "",
                        "author": str(metadata.get("/Author", "")) if "/Author" in metadata else "",
                        "subject": str(metadata.get("/Subject", "")) if "/Subject" in metadata else "",
                        "creator": str(metadata.get("/Creator", "")) if "/Creator" in metadata else "",
                        "producer": str(metadata.get("/Producer", "")) if "/Producer" in metadata else "",
                        "creation_date": str(metadata.get("/CreationDate", "")) if "/CreationDate" in metadata else "",
                        "modification_date": str(metadata.get("/ModDate", "")) if "/ModDate" in metadata else ""
                    }
                    
                    # Verificar metadata suspeita
                    suspicious_creators = ['malware', 'virus', 'exploit', 'hack']
                    creator = result["metadata"]["creator"].lower()
                    producer = result["metadata"]["producer"].lower()
                    
                    for suspicious in suspicious_creators:
                        if suspicious in creator or suspicious in producer:
                            result["suspicious_metadata"] = True
                            result["warnings"].append(f"Metadata suspeita detectada: {suspicious}")
                
        except Exception as e:
            logger.error(f"Erro ao verificar metadata do PDF: {e}")
            result["warnings"].append(f"Erro na análise de metadata: {str(e)}")
        
        return result
    
    def get_security_report(self) -> Dict:
        """Retorna relatório detalhado da última validação"""
        return self.last_validation_details.copy() if self.last_validation_details else {}


# Singleton para uso global
pdf_security_validator: Optional[PDFSecurityValidator] = None


def get_pdf_security_validator() -> PDFSecurityValidator:
    """Retorna a instância global do validador de segurança PDF"""
    global pdf_security_validator
    if pdf_security_validator is None:
        pdf_security_validator = PDFSecurityValidator()
    return pdf_security_validator


def validate_pdf_security(file_path: str) -> Dict:
    """Função de conveniência para validar segurança de PDF"""
    validator = get_pdf_security_validator()
    return validator.validate_pdf_security(file_path)
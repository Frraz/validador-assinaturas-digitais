import os
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional

# Importação das bibliotecas para validação criptográfica
from PyPDF2 import PdfReader
import asn1crypto
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.x509 import Certificate
from cryptography.exceptions import InvalidSignature
from pyhanko.sign.validation import validate_pdf_signature, validate_pdf_ltv
from pyhanko.sign.general import load_cert_from_pemder
from pyhanko_certvalidator import ValidationContext
from pyhanko_certvalidator.errors import PathValidationError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('assinatura_validator')


def validate_signature(file_path: str) -> Dict[str, Any]:
    """
    Valida a assinatura digital de um arquivo PDF seguindo padrões do ITI
    
    Args:
        file_path: Caminho para o arquivo PDF a ser validado
    
    Returns:
        Um dicionário contendo informações sobre a validação
    """
    if not os.path.exists(file_path):
        return {
            "valid": False,
            "error": "Arquivo não encontrado",
            "filename": os.path.basename(file_path)
        }
    
    try:
        # Verificação inicial do PDF
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            
            # Verificar se o PDF tem assinaturas
            has_signatures = has_pdf_signatures(pdf)
            
            if not has_signatures:
                return {
                    "valid": False,
                    "error": "Documento não contém assinaturas digitais",
                    "filename": os.path.basename(file_path)
                }
        
        # Extrair e validar assinaturas do PDF usando PyHanko
        validated_signatures = validate_signatures_cryptographically(file_path)
        
        # Analisar os resultados
        valid_signatures = [sig for sig in validated_signatures if sig["is_valid"]]
        invalid_signatures = [sig for sig in validated_signatures if not sig["is_valid"]]
        
        # Um documento é considerado válido se tem pelo menos uma assinatura válida
        is_valid = len(valid_signatures) > 0
        
        result = {
            "valid": is_valid,
            "total_signatures": len(validated_signatures),
            "valid_signatures": valid_signatures,
            "invalid_signatures": invalid_signatures,
            "filename": os.path.basename(file_path)
        }
        
        # Adicionar mensagem de erro se todas as assinaturas forem inválidas
        if not is_valid and invalid_signatures:
            errors = [sig.get("error", "Erro desconhecido") for sig in invalid_signatures]
            result["error"] = f"Todas as assinaturas são inválidas: {'; '.join(errors)}"
            
        return result
        
    except Exception as e:
        logger.exception("Erro ao validar assinatura")
        return {
            "valid": False,
            "error": f"Erro na validação da assinatura: {str(e)}",
            "filename": os.path.basename(file_path)
        }


def has_pdf_signatures(pdf: PdfReader) -> bool:
    """
    Verifica se um PDF contém campos de assinatura
    
    Args:
        pdf: Objeto PdfReader do PDF a ser verificado
        
    Returns:
        bool: True se o PDF contém assinaturas, False caso contrário
    """
    # Verificar presença de AcroForm com campos de assinatura
    if "/Root" in pdf.trailer:
        root = pdf.trailer["/Root"]
        if "/AcroForm" in root:
            acroform = root["/AcroForm"]
            if "/Fields" in acroform:
                fields = acroform["/Fields"]
                
                # Procurar por campos de assinatura
                for i in range(len(fields)):
                    try:
                        field = fields[i].get_object()
                        if "/FT" in field and field["/FT"] == "/Sig":
                            return True
                    except Exception as e:
                        logger.warning(f"Erro ao verificar campo de assinatura: {str(e)}")
    
    # Verificar presença de assinaturas nos dicionários de páginas
    for page_num in range(len(pdf.pages)):
        try:
            page = pdf.pages[page_num]
            if "/Annots" in page:
                annots = page["/Annots"]
                for i in range(len(annots)):
                    try:
                        annot = annots[i].get_object()
                        if "/Subtype" in annot and annot["/Subtype"] == "/Widget":
                            if "/FT" in annot and annot["/FT"] == "/Sig":
                                return True
                    except Exception as e:
                        logger.warning(f"Erro ao verificar anotação: {str(e)}")
        except Exception as e:
            logger.warning(f"Erro ao verificar página {page_num}: {str(e)}")
    
    return False


def validate_signatures_cryptographically(file_path: str) -> List[Dict[str, Any]]:
    """
    Valida criptograficamente todas as assinaturas em um PDF
    
    Args:
        file_path: Caminho para o arquivo PDF
        
    Returns:
        Lista de dicionários com informações de validação para cada assinatura
    """
    signatures = []
    
    try:
        # Abrir o PDF e obter informações das assinaturas
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            
            # Obter os campos de assinatura
            if "/Root" in pdf.trailer:
                root = pdf.trailer["/Root"]
                if "/AcroForm" in root:
                    acroform = root["/AcroForm"]
                    if "/Fields" in acroform:
                        fields = acroform["/Fields"]
                        
                        for i in range(len(fields)):
                            try:
                                field = fields[i].get_object()
                                
                                # Verificar se é um campo de assinatura
                                if "/FT" in field and field["/FT"] == "/Sig" and "/V" in field:
                                    sig_dict = field["/V"]
                                    
                                    # Extrair dados básicos da assinatura
                                    name = sig_dict.get("/Name", "") if "/Name" in sig_dict else ""
                                    date = sig_dict.get("/M", "") if "/M" in sig_dict else ""
                                    reason = sig_dict.get("/Reason", "") if "/Reason" in sig_dict else ""
                                    location = sig_dict.get("/Location", "") if "/Location" in sig_dict else ""
                                    
                                    # Converter a data para formato legível
                                    signing_time = format_pdf_date(date)
                                    
                                    # Extrair o certificado e validar a assinatura
                                    signature_info = {
                                        "signer": name,
                                        "signing_time": signing_time,
                                        "reason": reason,
                                        "location": location,
                                        "is_valid": False,
                                        "details": {}
                                    }
                                    
                                    # Validar a assinatura usando PyHanko
                                    validation_result = validate_signature_with_pyhanko(file_path, field)
                                    
                                    # Atualizar informações de validação
                                    signature_info["is_valid"] = validation_result["is_valid"]
                                    signature_info["details"] = validation_result["details"]
                                    
                                    if not validation_result["is_valid"]:
                                        signature_info["error"] = validation_result["error"]
                                        
                                    signatures.append(signature_info)
                            except Exception as e:
                                logger.error(f"Erro ao processar campo de assinatura: {e}")
                                signatures.append({
                                    "signer": "Desconhecido",
                                    "is_valid": False,
                                    "error": f"Erro ao processar assinatura: {str(e)}"
                                })
    
    except Exception as e:
        logger.exception("Falha ao extrair informações das assinaturas")
        signatures.append({
            "signer": "Desconhecido",
            "is_valid": False,
            "error": f"Falha ao extrair informações das assinaturas: {str(e)}"
        })
    
    return signatures


def validate_signature_with_pyhanko(file_path: str, sig_field) -> Dict[str, Any]:
    """
    Valida uma assinatura digital usando PyHanko
    
    Args:
        file_path: Caminho para o arquivo PDF
        sig_field: Campo de assinatura a ser validado
        
    Returns:
        Dicionário com resultado da validação
    """
    try:
        # Criar contexto de validação
        validation_context = ValidationContext(allow_fetching=True)
        
        # Criar arquivo temporário para validação
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            
            # Copiar o arquivo para o temporário
            with open(file_path, 'rb') as src_file:
                tmp.write(src_file.read())
                
        # Validar a assinatura usando PyHanko
        with open(tmp_path, 'rb') as tmp_file:
            # Obter o nome do campo de assinatura
            field_name = None
            if "/T" in sig_field:
                field_name = sig_field["/T"]
                
            # Se não conseguirmos obter o nome do campo, usaremos PyPDF2 diretamente
            if not field_name:
                return {
                    "is_valid": False,
                    "error": "Não foi possível determinar o nome do campo de assinatura",
                    "details": {}
                }
                
            # Usar PyHanko para validar
            try:
                from pyhanko.pdf_utils.reader import PdfFileReader
                from pyhanko.sign.validation import read_certification_data, SignatureCoverageLevel
                
                pdf_reader = PdfFileReader(tmp_file)
                sig_obj = pdf_reader.embedded_signatures[0]  # Tentar validar a primeira assinatura
                
                status = validate_pdf_signature(
                    sig_obj,
                    validation_context=validation_context,
                    skip_timestamp=False
                )
                
                # Verificar status de integridade
                integrity_valid = status.valid
                cert_valid = status.cert_status.valid
                
                details = {
                    "integrity_check": "OK" if integrity_valid else "Falhou",
                    "certificate_status": "Válido" if cert_valid else "Inválido",
                    "signature_type": str(status.coverage),
                    "timestamp_valid": "Sim" if status.timestamp_validity and status.timestamp_validity.valid else "Não"
                }
                
                # Verificar se é uma assinatura ICP-Brasil (simplificado)
                if cert_valid:
                    cert = status.cert_status.certificate
                    is_icp_brasil = check_if_icp_brasil(cert)
                    details["is_icp_brasil"] = is_icp_brasil
                    
                # Verificar LCR
                if status.cert_status.revocation_status:
                    revoked = status.cert_status.revocation_status.revoked
                    details["revocation_status"] = "Revogado" if revoked else "Não revogado"
                else:
                    details["revocation_status"] = "Não verificado"
                
                # Determinar resultado final
                is_valid = integrity_valid and cert_valid
                
                result = {
                    "is_valid": is_valid,
                    "details": details
                }
                
                if not is_valid:
                    error_reasons = []
                    if not integrity_valid:
                        error_reasons.append("Falha na verificação da integridade da assinatura")
                    if not cert_valid:
                        error_reasons.append("Certificado inválido ou expirado")
                    
                    result["error"] = "; ".join(error_reasons) or "Assinatura inválida"
                
                return result
                
            except Exception as e:
                logger.exception(f"Erro ao validar com PyHanko: {e}")
                return {
                    "is_valid": False,
                    "error": f"Erro na validação com PyHanko: {str(e)}",
                    "details": {}
                }
                
    except Exception as e:
        logger.exception(f"Erro geral na validação da assinatura: {e}")
        return {
            "is_valid": False,
            "error": f"Erro geral na validação: {str(e)}",
            "details": {}
        }
    finally:
        # Limpar arquivo temporário
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def check_if_icp_brasil(cert) -> bool:
    """
    Verifica se um certificado pertence à ICP-Brasil
    
    Args:
        cert: Objeto de certificado
        
    Returns:
        bool: True se for certificado da ICP-Brasil, False caso contrário
    """
    try:
        # OID da ICP-Brasil (simplificado)
        ICP_BRASIL_OID = "2.16.76.1.2"  # OID base para certificados ICP-Brasil
        
        # Verificar se o certificado contém algum OID da ICP-Brasil
        for extension in cert.extensions:
            oid_str = str(extension.oid.dotted_string)
            if oid_str.startswith(ICP_BRASIL_OID):
                return True
                
        # Verificar no emissor se contém informações da ICP-Brasil
        issuer_str = cert.issuer.human_readable
        if "ICP-Brasil" in issuer_str or "AC-Raiz" in issuer_str:
            return True
            
        return False
        
    except Exception:
        logger.exception("Erro ao verificar se certificado é ICP-Brasil")
        return False


def format_pdf_date(date_str):
    """
    Formata uma data no formato PDF para um formato legível
    
    Args:
        date_str: String de data no formato PDF
        
    Returns:
        String de data formatada
    """
    if not date_str or not isinstance(date_str, str):
        return "Desconhecido"
    
    if date_str.startswith("D:"):
        # Formato típico: D:YYYYMMDDHHmmSS
        try:
            date_str = date_str[2:]  # Remover 'D:'
            dt = datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            pass
    
    return date_str
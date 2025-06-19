import os
import base64
import tempfile
import datetime

def extract_certificate_info(certificate):
    """
    Extrai informações do certificado
    
    Args:
        certificate: Objeto certificado (dependendo da biblioteca)
        
    Returns:
        Um dicionário contendo informações do certificado
    """
    # Esta é uma implementação simplificada
    # Em um ambiente real, você extrairia mais informações do certificado
    
    info = {
        "subject": str(certificate.subject) if hasattr(certificate, "subject") else "Desconhecido",
        "issuer": str(certificate.issuer) if hasattr(certificate, "issuer") else "Desconhecido",
        "valid_from": format_date(certificate.not_valid_before) if hasattr(certificate, "not_valid_before") else "Desconhecido",
        "valid_until": format_date(certificate.not_valid_after) if hasattr(certificate, "not_valid_after") else "Desconhecido",
        "serial_number": str(certificate.serial_number) if hasattr(certificate, "serial_number") else "Desconhecido",
    }
    
    # Extrair informações do Subject (Nome, CPF/CNPJ, etc)
    if hasattr(certificate, "subject"):
        for attr in certificate.subject:
            key = attr.oid._name
            value = attr.value
            if key == "commonName":
                info["common_name"] = value
            elif key == "organizationName":
                info["organization"] = value
    
    return info


def verify_certificate_chain(certificate, trusted_certs=None):
    """
    Verifica a cadeia de certificados
    
    Args:
        certificate: O certificado a ser verificado
        trusted_certs: Lista de certificados confiáveis
        
    Returns:
        Um booleano indicando se o certificado é válido e um dicionário com informações adicionais
    """
    # Em uma implementação real, esta função verificaria:
    # - Se o certificado foi emitido por uma Autoridade Certificadora confiável
    # - Se o certificado não está revogado (consulta CRL/OCSP)
    # - Se o certificado não está expirado
    
    # Esta é uma implementação simulada
    now = datetime.datetime.now()
    
    is_valid = True
    details = {
        "chain_verified": True,
        "not_revoked": True,
        "not_expired": True
    }
    
    # Verificar validade temporal
    if hasattr(certificate, "not_valid_before") and hasattr(certificate, "not_valid_after"):
        if certificate.not_valid_before > now or certificate.not_valid_after < now:
            is_valid = False
            details["not_expired"] = False
    
    return is_valid, details


def format_date(date):
    """Formata data para exibição"""
    if not date:
        return "Desconhecido"
    
    if isinstance(date, datetime.datetime):
        return date.strftime("%d/%m/%Y %H:%M:%S")
    
    return str(date)
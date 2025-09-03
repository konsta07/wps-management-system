# models/__init__.py - ДОЛЖНО БЫТЬ ТАК:
from .company import Company
from .wps import WPS  
from .wpqr import WPQR
from .user import User
from .welder import Welder, WelderCertificate

__all__ = ["Company", "WPS", "WPQR", "User"]
"""
Sistema de gerenciamento de reservas in-memory.
Será substituído por banco de dados em produção.
"""
import json
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from app.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class Reservation:
    """Modelo de reserva simplificado."""
    code: str
    guest_name: str
    guest_phone: str
    guest_document: str
    check_in: str  # ISO format
    check_out: str  # ISO format
    adults: int
    children: List[int]
    room_type: str
    meal_plan: str
    total_amount: float
    status: str = "confirmed"
    created_at: str = None
    confirmed_at: str = None
    payment_status: str = "pending"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

class ReservationManager:
    """Gerenciador de reservas em memória."""
    
    def __init__(self):
        self._reservations: Dict[str, Reservation] = {}
        self._by_phone: Dict[str, List[str]] = {}
    
    def create_reservation(
        self,
        code: str,
        guest_name: str,
        guest_phone: str,
        guest_document: str,
        check_in: date,
        check_out: date,
        adults: int,
        children: List[int],
        room_type: str,
        meal_plan: str,
        total_amount: float
    ) -> Reservation:
        """Cria uma nova reserva."""
        reservation = Reservation(
            code=code,
            guest_name=guest_name,
            guest_phone=guest_phone,
            guest_document=guest_document,
            check_in=check_in.isoformat(),
            check_out=check_out.isoformat(),
            adults=adults,
            children=children,
            room_type=room_type,
            meal_plan=meal_plan,
            total_amount=total_amount,
            confirmed_at=datetime.now().isoformat()
        )
        
        # Salva a reserva
        self._reservations[code] = reservation
        
        # Indexa por telefone
        if guest_phone not in self._by_phone:
            self._by_phone[guest_phone] = []
        self._by_phone[guest_phone].append(code)
        
        logger.info(
            "Reserva criada",
            code=code,
            guest_name=guest_name,
            guest_phone=guest_phone,
            total_amount=total_amount
        )
        
        return reservation
    
    def get_reservation(self, code: str) -> Optional[Reservation]:
        """Busca uma reserva pelo código."""
        return self._reservations.get(code)
    
    def get_reservations_by_phone(self, phone: str) -> List[Reservation]:
        """Busca todas as reservas de um telefone."""
        codes = self._by_phone.get(phone, [])
        return [self._reservations[code] for code in codes if code in self._reservations]
    
    def update_payment_status(self, code: str, status: str) -> bool:
        """Atualiza o status do pagamento."""
        if code in self._reservations:
            self._reservations[code].payment_status = status
            logger.info("Payment status updated", code=code, status=status)
            return True
        return False
    
    def update_guest_data(
        self,
        code: str,
        guest_name: str = None,
        guest_document: str = None
    ) -> bool:
        """Atualiza dados do hóspede."""
        if code in self._reservations:
            reservation = self._reservations[code]
            if guest_name:
                reservation.guest_name = guest_name
            if guest_document:
                reservation.guest_document = guest_document
            logger.info("Guest data updated", code=code)
            return True
        return False
    
    def cancel_reservation(self, code: str, reason: str = None) -> bool:
        """Cancela uma reserva."""
        if code in self._reservations:
            self._reservations[code].status = "cancelled"
            logger.info("Reservation cancelled", code=code, reason=reason)
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas das reservas."""
        total = len(self._reservations)
        confirmed = sum(1 for r in self._reservations.values() if r.status == "confirmed")
        cancelled = sum(1 for r in self._reservations.values() if r.status == "cancelled")
        total_revenue = sum(r.total_amount for r in self._reservations.values() if r.status == "confirmed")
        
        return {
            "total_reservations": total,
            "confirmed": confirmed,
            "cancelled": cancelled,
            "total_revenue": total_revenue
        }
    
    def export_data(self) -> str:
        """Exporta todas as reservas para JSON."""
        data = {
            "reservations": {code: asdict(res) for code, res in self._reservations.items()},
            "by_phone": self._by_phone,
            "exported_at": datetime.now().isoformat()
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def import_data(self, json_data: str) -> bool:
        """Importa reservas de JSON."""
        try:
            data = json.loads(json_data)
            
            # Importa reservas
            for code, res_data in data.get("reservations", {}).items():
                self._reservations[code] = Reservation(**res_data)
            
            # Importa índice por telefone
            self._by_phone = data.get("by_phone", {})
            
            logger.info("Data imported successfully", total_reservations=len(self._reservations))
            return True
        except Exception as e:
            logger.error("Failed to import data", error=str(e))
            return False

# Instância global (será substituída por banco de dados)
_reservation_manager = None

def get_reservation_manager() -> ReservationManager:
    """Retorna a instância global do gerenciador de reservas."""
    global _reservation_manager
    if _reservation_manager is None:
        _reservation_manager = ReservationManager()
    return _reservation_manager

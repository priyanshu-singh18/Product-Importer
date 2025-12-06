"""
Validator Registry for extensible product validation
Implements Registry Pattern for pluggable validators
"""

from typing import Callable, Optional


class ProductValidatorRegistry:
    """Registry for product validators - easily add custom validation rules"""

    _validators: list[Callable[[dict], Optional[str]]] = []

    @classmethod
    def register(cls, validator_func: Callable[[dict], Optional[str]]):
        """
        Register a validator function.

        Validator should accept a dict (CSV row) and return:
        - None if valid
        - Error message string if invalid

        Example:
            @ProductValidatorRegistry.register
            def validate_price_positive(row):
                price = row.get('price')
                if price and float(price) < 0:
                    return "Price must be positive"
        """
        cls._validators.append(validator_func)
        return validator_func

    @classmethod
    def validate(cls, row: dict) -> list[str]:
        """Run all registered validators on a row"""
        errors = []
        for validator in cls._validators:
            error = validator(row)
            if error:
                errors.append(error)
        return errors

    @classmethod
    def clear(cls):
        """Clear all validators (useful for testing)"""
        cls._validators = []

package com.lipari.bank.movement.dto;

import java.math.BigDecimal;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class TransferRequest {
    @NotNull
    private Long fromAccountId;

    @NotNull
    private Long toAccountId;

    @NotNull
    @DecimalMin(value = "0.01", message = "amount must be > 0")
    private BigDecimal amount;

    private String description;
}

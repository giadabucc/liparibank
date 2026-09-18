package com.lipari.bank.movement.dto;

import java.math.BigDecimal;
import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class TransferResponse {
    private Long transferId;
    private BigDecimal fromBalance;
    private BigDecimal toBalance;
    private String status;
}

package com.lipari.bank.movement;

import java.math.BigDecimal;
import java.time.Instant;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Table(name = "movement")
@Data
public class Movement {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "account_id", nullable = false)
    private Long accountId;

    @Column(nullable = false)
    private String type;   // DEPOSIT, WITHDRAW, TRANSFER_OUT, TRANSFER_IN

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal amount;

    @Column(name = "counterparty_account_id")
    private Long counterpartyAccountId;

    private String description;

    @Column(name = "executed_at")
    private Instant executedAt;
}

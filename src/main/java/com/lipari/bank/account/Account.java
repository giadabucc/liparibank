package com.lipari.bank.account;

import java.math.BigDecimal;
import java.time.Instant;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Table(name = "account")
@Data
public class Account {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "customer_id", nullable = false)
    private Long customerId;

    @Column(nullable = false, unique = true)
    private String iban;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal balance;

    @Column(nullable = false)
    private String currency = "EUR";

    @Column(nullable = false)
    private String status = "ACTIVE";

    @Column(name = "created_at")
    private Instant createdAt;
}

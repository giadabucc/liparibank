package com.lipari.bank.customer;

import java.time.Instant;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Table(name = "customer")
@Data
public class Customer {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "first_name", nullable = false)
    private String firstName;

    @Column(name = "last_name", nullable = false)
    private String lastName;

    @Column(name = "fiscal_code", nullable = false, unique = true)
    private String fiscalCode;

    @Column(name = "created_at")
    private Instant createdAt;
}

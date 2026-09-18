package com.lipari.bank.movement;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MovementRepository extends JpaRepository<Movement, Long> {
    List<Movement> findByAccountIdOrderByExecutedAtDesc(Long accountId);
}

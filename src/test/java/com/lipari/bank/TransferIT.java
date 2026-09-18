package com.lipari.bank;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import com.lipari.bank.movement.MovementService;
import com.lipari.bank.movement.dto.TransferRequest;
import com.lipari.bank.movement.dto.TransferResponse;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class TransferIT {

    @Autowired private MovementService movementService;

    @Test
    void happyPathTransfer() {
        TransferRequest req = new TransferRequest();
        req.setFromAccountId(1L);
        req.setToAccountId(2L);
        req.setAmount(new BigDecimal("100.00"));
        req.setDescription("demo transfer");

        TransferResponse resp = movementService.transfer(req);

        assertThat(resp.getStatus()).isEqualTo("COMPLETED");
        assertThat(resp.getFromBalance()).isEqualByComparingTo("900.00");
        assertThat(resp.getToBalance()).isEqualByComparingTo("600.00");
    }
}

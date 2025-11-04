CREATE TABLE IF NOT EXISTS funcionarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  cargo VARCHAR(120) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS maquinas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  descricao TEXT,
  ativo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ordens_servico (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_maquina INT NOT NULL,
  id_funcionario INT,
  tipo_de_servico VARCHAR(120) NOT NULL,
  local_do_problema VARCHAR(200),
  descricao_do_problema TEXT,
  datahora_inicio DATETIME,
  datahora_fim DATETIME,
  concluido TINYINT(1) NOT NULL DEFAULT 0,
  observacao TEXT,
  CONSTRAINT fk_os_maquina FOREIGN KEY (id_maquina) REFERENCES maquinas(id),
  CONSTRAINT fk_os_funcionario FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ordens_preventiva (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_maquina INT NOT NULL,
  id_funcionario INT,
  datahora_inicio DATETIME,
  datahora_fim DATETIME,
  servico_realizado TEXT,
  status VARCHAR(60) NOT NULL DEFAULT 'Aberta',
  CONSTRAINT fk_prev_maquina FOREIGN KEY (id_maquina) REFERENCES maquinas(id),
  CONSTRAINT fk_prev_funcionario FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- N:1 mão-de-obra por OS
CREATE TABLE IF NOT EXISTS mao_obra_os (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_ordem_servico INT NOT NULL,
  id_funcionario INT NOT NULL,
  data DATE NOT NULL,
  hora_inicio TIME NOT NULL,
  hora_fim TIME NOT NULL,
  CONSTRAINT fk_mo_os_os FOREIGN KEY (id_ordem_servico) REFERENCES ordens_servico(id),
  CONSTRAINT fk_mo_os_func FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- N:1 mão-de-obra por Preventiva
CREATE TABLE IF NOT EXISTS mao_obra_preventiva (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_ordem_preventiva INT NOT NULL,
  id_funcionario INT NOT NULL,
  data DATE NOT NULL,
  hora_inicio TIME NOT NULL,
  hora_fim TIME NOT NULL,
  CONSTRAINT fk_mo_prev_prev FOREIGN KEY (id_ordem_preventiva) REFERENCES ordens_preventiva(id),
  CONSTRAINT fk_mo_prev_func FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Mantemos sua tabela de OEE conforme já vinha usando
-- Ajuste o nome se o seu for outro:
CREATE TABLE IF NOT EXISTS oee_registros (
  Id INT AUTO_INCREMENT PRIMARY KEY,
  linha INT NOT NULL,
  inicio DATETIME NOT NULL,
  fim DATETIME NOT NULL,
  disponivel INT NOT NULL,
  produzindo INT NOT NULL,
  parada INT NOT NULL,
  producao INT NOT NULL,
  rejeito INT NOT NULL,
  disponibilidade FLOAT NOT NULL,
  performance FLOAT NOT NULL,
  qualidade FLOAT NOT NULL,
  oee FLOAT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


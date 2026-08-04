# Farm-innstillinger og bankkontoer

Farm-innstillinger og bankkontoer er Farm-scopet og bruker `/farm_id` i egne deklarerte Cosmos-containere. Runtime oppretter aldri containere. Owner administrerer bankkontoer i MVP; manager kan lese og oppdatere Farm-innstillinger.

Bankkontoer valideres som norske 11-sifrede modulus-11-kontonumre, listes maskert og deaktiveres soft. De er ikke verifisert mot bank, og betaling eller bankintegrasjon er ikke implementert.

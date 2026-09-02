# Migrationsnotizen

Die öffentliche Factory `create_chappie_backend()` und `init_chappie()` bleiben
über `web_infrastructure/backend_wrapper.py` kompatibel. Die vormals
verschachtelte Klasse ist nun als `CHAPPiERuntime` auf Modulebene definiert;
`CHAPPiEBackend` bleibt ein Klassenalias.

Sync und Streaming verwenden denselben typisierten Turn-Einstieg. Unterschiedlich
bleiben ausschließlich ihre Ausgabeadapter und die providerseitige
Stream-Verarbeitung. Providerwahl, Sampling, Steering, Memory-, Life- und
SSE-Semantik wurden bei der Extraktion nicht neu festgelegt.


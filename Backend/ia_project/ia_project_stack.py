from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
)
from aws_cdk.aws_ecr_assets import Platform
from constructs import Construct

class AuthConstruct(Construct):
    """
    Construct to handle Authentication resources (Cognito)
    """
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        self.user_pool = cognito.UserPool(self, "IaProjectUserPool",
            user_pool_name="ia-project-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True, username=False),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            removal_policy=RemovalPolicy.DESTROY  # Change to RETAIN for production
        )

        self.user_pool_client = self.user_pool.add_client("IaProjectUserPoolClient",
            user_pool_client_name="ia-project-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            )
        )

class BackendConstruct(Construct):
    """
    Construct to handle Backend resources (Lambda + API Gateway + DynamoDB)
    """
    def __init__(self, scope: Construct, id: str, user_pool: cognito.UserPool, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Crear tabla DynamoDB (On-Demand)
        self.table = dynamodb.Table(self, "TarifasLogisticaTable",
            table_name="TarifasLogistica",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, # No aprovisionada (On-demand)
            removal_policy=RemovalPolicy.DESTROY # NOT RECOMMENDED for production
        )

        # Índices Globales Secundarios (GSI)
        # 1. Búsqueda por Origen
        self.table.add_global_secondary_index(
            index_name="OrigenIndex",
            partition_key=dynamodb.Attribute(name="origen", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 2. Búsqueda por Destino
        self.table.add_global_secondary_index(
            index_name="DestinoIndex",
            partition_key=dynamodb.Attribute(name="destino", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 3. Búsqueda por Proveedor
        self.table.add_global_secondary_index(
            index_name="ProveedorIndex",
            partition_key=dynamodb.Attribute(name="proveedor", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 4. (Opcional pero recomendado) Búsqueda por Ruta (Origen -> Destino)
        # Esto permite queries eficientes como: "Dame tarifas de Puerto Quetzal a Mixco"
        self.table.add_global_secondary_index(
            index_name="RutaIndex",
            partition_key=dynamodb.Attribute(name="origen", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="destino", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # ===== LAMBDA FUNCTIONS PARA CRUD =====
        
        # CREATE - Crear nueva tarifa
        self.create_handler = _lambda.Function(self, "CreateTarifaHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/tarifas_crud"),
            handler="create.handler",
            description="Create new tarifa",
            environment={"TABLE_NAME": self.table.table_name}
        )
        self.table.grant_write_data(self.create_handler)
        
        # READ - Leer tarifas (una o todas)
        self.read_handler = _lambda.Function(self, "ReadTarifaHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/tarifas_crud"),
            handler="read.handler",
            description="Read tarifas",
            environment={"TABLE_NAME": self.table.table_name}
        )
        self.table.grant_read_data(self.read_handler)
        
        # UPDATE - Actualizar tarifa existente
        self.update_handler = _lambda.Function(self, "UpdateTarifaHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/tarifas_crud"),
            handler="update.handler",
            description="Update tarifa",
            environment={"TABLE_NAME": self.table.table_name}
        )
        self.table.grant_read_write_data(self.update_handler)
        
        # DELETE - Eliminar tarifa
        self.delete_handler = _lambda.Function(self, "DeleteTarifaHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/tarifas_crud"),
            handler="delete.handler",
            description="Delete tarifa",
            environment={"TABLE_NAME": self.table.table_name}
        )
        self.table.grant_read_write_data(self.delete_handler)

        # ===== CHATBOT TERRESTRE LAMBDA (Docker / ECR) =====

        self.chatbot_handler = _lambda.DockerImageFunction(self, "ChatbotTerrestreHandler",
            code=_lambda.DockerImageCode.from_image_asset("lambda/chatbot",
                platform=Platform.LINUX_AMD64,
                cmd=["chatbot_terrestre.handler"]
            ),
            description="AI chatbot terrestre using Amazon Nova Pro via Bedrock",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "TABLE_NAME": self.table.table_name,
                "REGION": Stack.of(self).region,
                "MODEL_ID": "amazon.nova-pro-v1:0",
            }
        )

        # DynamoDB read access for the terrestre chatbot
        self.table.grant_read_data(self.chatbot_handler)

        # Bedrock invocation permission for terrestre chatbot
        self.chatbot_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # ===== DYNAMODB TABLE FOR MARITIME QUOTATIONS (ALCE V2) =====

        self.maritime_table = dynamodb.Table(self, "MaritimeQuotationsTable",
            table_name="MaritimeQuotations",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY  # NOT RECOMMENDED for production
        )

        # GSI 1: Query by origin port
        self.maritime_table.add_global_secondary_index(
            index_name="OriginPortIndex",
            partition_key=dynamodb.Attribute(name="origin_port", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI 2: Query by destination port
        self.maritime_table.add_global_secondary_index(
            index_name="DestinationPortIndex",
            partition_key=dynamodb.Attribute(name="destination_port", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI 3: Query by shipping line (naviera)
        self.maritime_table.add_global_secondary_index(
            index_name="ShippingLineIndex",
            partition_key=dynamodb.Attribute(name="shipping_line", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # ===== LAMBDA FUNCTIONS FOR MARITIME CRUD =====

        # CREATE - Create new maritime quotation
        self.create_maritime_handler = _lambda.Function(self, "CreateMaritimeHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/maritime_crud"),
            handler="create.handler",
            description="Create new maritime quotation (ALCE V2)",
            environment={"TABLE_NAME": self.maritime_table.table_name}
        )
        self.maritime_table.grant_write_data(self.create_maritime_handler)

        # READ - Read maritime quotations (one or all)
        self.read_maritime_handler = _lambda.Function(self, "ReadMaritimeHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/maritime_crud"),
            handler="read.handler",
            description="Read maritime quotations (ALCE V2)",
            environment={"TABLE_NAME": self.maritime_table.table_name}
        )
        self.maritime_table.grant_read_data(self.read_maritime_handler)

        # UPDATE - Update existing maritime quotation
        self.update_maritime_handler = _lambda.Function(self, "UpdateMaritimeHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/maritime_crud"),
            handler="update.handler",
            description="Update maritime quotation (ALCE V2)",
            environment={"TABLE_NAME": self.maritime_table.table_name}
        )
        self.maritime_table.grant_read_write_data(self.update_maritime_handler)

        # DELETE - Delete maritime quotation
        self.delete_maritime_handler = _lambda.Function(self, "DeleteMaritimeHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/maritime_crud"),
            handler="delete.handler",
            description="Delete maritime quotation (ALCE V2)",
            environment={"TABLE_NAME": self.maritime_table.table_name}
        )
        self.maritime_table.grant_read_write_data(self.delete_maritime_handler)

        # ===== CHATBOT MARITIMO LAMBDA (Docker / ECR — same image as terrestre) =====

        self.chatbot_maritimo_handler = _lambda.DockerImageFunction(self, "ChatbotMaritimoHandler",
            code=_lambda.DockerImageCode.from_image_asset("lambda/chatbot",
                platform=Platform.LINUX_AMD64,
                cmd=["chatbot_maritimo.handler"]
            ),
            description="AI chatbot maritimo ALCE V2 using Amazon Nova Pro via Bedrock",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "MARITIME_TABLE_NAME": self.maritime_table.table_name,
                "REGION": Stack.of(self).region,
                "MODEL_ID": "amazon.nova-pro-v1:0",
            }
        )

        # DynamoDB read access for the maritime chatbot
        self.maritime_table.grant_read_data(self.chatbot_maritimo_handler)

        # Bedrock invocation permission for maritime chatbot
        self.chatbot_maritimo_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # ===== API GATEWAY =====

        self.api = apigw.RestApi(self, "IaProjectApi",
            rest_api_name="IA Project Service",
            description="This service handles IA project requests.",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=['Content-Type', 'Authorization', 'X-Amz-Date', 'X-Api-Key', 'X-Amz-Security-Token']
            )
        )

        # Authorizer (opcional - puedes comentarlo si no quieres autenticación)
        # authorizer = apigw.CognitoUserPoolsAuthorizer(self, "IaProjectAuthorizer",
        #     cognito_user_pools=[user_pool]
        # )

        # ===== ENDPOINTS CRUD TERRESTRE =====

        # Recurso /tarifas
        tarifas = self.api.root.add_resource("tarifas")

        # POST /tarifas - Crear nueva tarifa
        tarifas.add_method("POST",
            apigw.LambdaIntegration(self.create_handler),
            # Descomenta la siguiente línea si quieres autenticación
            # authorizer=authorizer,
            # authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /tarifas - Listar todas las tarifas (con filtros opcionales)
        tarifas.add_method("GET",
            apigw.LambdaIntegration(self.read_handler),
            # Descomenta la siguiente línea si quieres autenticación
            # authorizer=authorizer,
            # authorization_type=apigw.AuthorizationType.COGNITO
        )

        # Recurso /tarifas/{id}
        tarifa_by_id = tarifas.add_resource("{id}")

        # GET /tarifas/{id} - Obtener tarifa específica
        tarifa_by_id.add_method("GET",
            apigw.LambdaIntegration(self.read_handler),
            # Descomenta la siguiente línea si quieres autenticación
            # authorizer=authorizer,
            # authorization_type=apigw.AuthorizationType.COGNITO
        )

        # PUT /tarifas/{id} - Actualizar tarifa
        tarifa_by_id.add_method("PUT",
            apigw.LambdaIntegration(self.update_handler),
            # Descomenta la siguiente línea si quieres autenticación
            # authorizer=authorizer,
            # authorization_type=apigw.AuthorizationType.COGNITO
        )

        # DELETE /tarifas/{id} - Eliminar tarifa
        tarifa_by_id.add_method("DELETE",
            apigw.LambdaIntegration(self.delete_handler),
            # Descomenta la siguiente línea si quieres autenticación
            # authorizer=authorizer,
            # authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ===== ENDPOINT CHATBOT TERRESTRE =====

        # POST /chatbot - Invocar chatbot terrestre
        chatbot = self.api.root.add_resource("chatbot")
        chatbot.add_method("POST",
            apigw.LambdaIntegration(self.chatbot_handler)
        )

        # ===== ENDPOINTS CRUD MARITIMO (ALCE V2) =====

        # Recurso /maritime-quotations
        maritime_quotations = self.api.root.add_resource("maritime-quotations")

        # POST /maritime-quotations - Crear nueva cotización marítima
        maritime_quotations.add_method("POST",
            apigw.LambdaIntegration(self.create_maritime_handler)
        )

        # GET /maritime-quotations - Listar / filtrar cotizaciones marítimas
        maritime_quotations.add_method("GET",
            apigw.LambdaIntegration(self.read_maritime_handler)
        )

        # Recurso /maritime-quotations/{id}
        maritime_by_id = maritime_quotations.add_resource("{id}")

        # GET /maritime-quotations/{id} - Obtener cotización marítima específica
        maritime_by_id.add_method("GET",
            apigw.LambdaIntegration(self.read_maritime_handler)
        )

        # PUT /maritime-quotations/{id} - Actualizar cotización marítima
        maritime_by_id.add_method("PUT",
            apigw.LambdaIntegration(self.update_maritime_handler)
        )

        # DELETE /maritime-quotations/{id} - Eliminar cotización marítima
        maritime_by_id.add_method("DELETE",
            apigw.LambdaIntegration(self.delete_maritime_handler)
        )

        # ===== ENDPOINT CHATBOT MARITIMO (ALCE V2) =====

        # POST /chatbot-maritimo - Invocar chatbot marítimo ALCE V2
        chatbot_maritimo = self.api.root.add_resource("chatbot-maritimo")
        chatbot_maritimo.add_method("POST",
            apigw.LambdaIntegration(self.chatbot_maritimo_handler)
        )

        # ===== CHATBOT CENTRAL LAMBDA (Docker / ECR — same image) =====

        self.chatbot_central_handler = _lambda.DockerImageFunction(self, "ChatbotCentralHandler",
            code=_lambda.DockerImageCode.from_image_asset("lambda/chatbot",
                platform=Platform.LINUX_AMD64,
                cmd=["chatbot_central.handler"]
            ),
            description="AI chatbot centralizado (terrestre + maritimo) con detección automática de dominio",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "TABLE_NAME": self.table.table_name,
                "MARITIME_TABLE_NAME": self.maritime_table.table_name,
                "REGION": Stack.of(self).region,
                "MODEL_ID": "amazon.nova-pro-v1:0",
            }
        )

        # DynamoDB read access for the central chatbot (both tables)
        self.table.grant_read_data(self.chatbot_central_handler)
        self.maritime_table.grant_read_data(self.chatbot_central_handler)

        # Bedrock invocation permission for central chatbot
        self.chatbot_central_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # ===== ENDPOINT CHATBOT CENTRAL =====

        # POST /chatbot-central - Invocar chatbot centralizado (auto-detección de dominio)
        chatbot_central = self.api.root.add_resource("chatbot-central")
        chatbot_central.add_method("POST",
            apigw.LambdaIntegration(self.chatbot_central_handler)
        )

        # ===== COTIZACIONES TABLE (unified for terrestrial + maritime) =====

        self.cotizaciones_table = dynamodb.Table(self, "CotizacionesTable",
            table_name="Cotizaciones",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN
        )

        # GSI: query by tipo (terrestre/maritimo)
        self.cotizaciones_table.add_global_secondary_index(
            index_name="TipoIndex",
            partition_key=dynamodb.Attribute(name="tipo", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # CREATE cotizacion Lambda
        self.create_cotizacion_handler = _lambda.Function(self, "CreateCotizacionHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/cotizaciones_crud"),
            handler="create.handler",
            description="Save accepted quotation to Cotizaciones table",
            environment={"TABLE_NAME": self.cotizaciones_table.table_name}
        )
        self.cotizaciones_table.grant_write_data(self.create_cotizacion_handler)

        # READ cotizaciones Lambda
        self.read_cotizacion_handler = _lambda.Function(self, "ReadCotizacionHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/cotizaciones_crud"),
            handler="read.handler",
            description="Read cotizaciones",
            environment={"TABLE_NAME": self.cotizaciones_table.table_name}
        )
        self.cotizaciones_table.grant_read_data(self.read_cotizacion_handler)

        # UPDATE cotizacion Lambda
        self.update_cotizacion_handler = _lambda.Function(self, "UpdateCotizacionHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/cotizaciones_crud"),
            handler="update.handler",
            description="Update an accepted cotizacion (add seller fields for shipping order)",
            environment={"TABLE_NAME": self.cotizaciones_table.table_name}
        )
        self.cotizaciones_table.grant_write_data(self.update_cotizacion_handler)

        # ===== ENDPOINTS /cotizaciones =====

        cotizaciones_resource = self.api.root.add_resource("cotizaciones")
        cotizaciones_resource.add_method("POST", apigw.LambdaIntegration(self.create_cotizacion_handler))
        cotizaciones_resource.add_method("GET", apigw.LambdaIntegration(self.read_cotizacion_handler))

        cotizacion_by_id = cotizaciones_resource.add_resource("{id}")
        cotizacion_by_id.add_method("GET", apigw.LambdaIntegration(self.read_cotizacion_handler))
        cotizacion_by_id.add_method("PUT", apigw.LambdaIntegration(self.update_cotizacion_handler))

class IaProjectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Usando Custom Constructs para organizar mejor la infraestructura
        auth = AuthConstruct(self, "Auth")
        
        BackendConstruct(self, "Backend",
            user_pool=auth.user_pool
        )

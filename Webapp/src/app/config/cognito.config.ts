
/**
 * AWS Cognito Configuration
 * 
 * User Pool: us-east-1_rOZcYSsNs
 * Client ID: 2mv4phm971j9b32hulgtjlda43
 * Region: us-east-1
 */

export const cognitoConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_rOZcYSsNs',
      userPoolClientId: '2mv4phm971j9b32hulgtjlda43',
      region: 'us-east-1',
      
      // Opciones de autenticación
      authenticationFlowType: 'USER_PASSWORD_AUTH',
      
      // Configuración de tokens
      cookieStorage: {
        domain: 'localhost',
        secure: false, // Set to true in production with HTTPS
        path: '/',
        expires: 7, // 7 days
      },
    }
  }
};

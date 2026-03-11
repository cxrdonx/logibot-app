import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, from, throwError } from 'rxjs';
import { map, catchError, switchMap } from 'rxjs/operators';
import { Amplify } from 'aws-amplify';
import { signIn, signOut, getCurrentUser, fetchAuthSession, SignInOutput, confirmSignIn } from 'aws-amplify/auth';
import { cognitoConfig } from '../config/cognito.config';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface User {
  id: string;
  username: string;
  email?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly TOKEN_KEY = 'logibot_auth_token';
  private readonly USER_KEY = 'logibot_current_user';
  private readonly PENDING_PASSWORD_CHANGE = 'logibot_pending_password_change';

  private currentUserSubject: BehaviorSubject<User | null>;
  public currentUser$: Observable<User | null>;

  private isAuthenticatedSubject: BehaviorSubject<boolean>;
  public isAuthenticated$: Observable<boolean>;

  // Store pending password change state
  private pendingPasswordChangeSubject: BehaviorSubject<boolean>;
  public pendingPasswordChange$: Observable<boolean>;

  constructor() {
    // Configure Amplify with Cognito
    Amplify.configure(cognitoConfig);

    // Initialize from localStorage (only available in browser)
    let savedUser = null;
    let token = null;
    let pendingPasswordChange = false;

    // Check if localStorage is available (not in SSR context)
    if (typeof localStorage !== 'undefined') {
      const userStr = localStorage.getItem(this.USER_KEY);
      savedUser = userStr ? JSON.parse(userStr) : null;
      token = localStorage.getItem(this.TOKEN_KEY);
      pendingPasswordChange = localStorage.getItem(this.PENDING_PASSWORD_CHANGE) === 'true';
    }

    this.currentUserSubject = new BehaviorSubject<User | null>(savedUser);
    this.currentUser$ = this.currentUserSubject.asObservable();

    this.isAuthenticatedSubject = new BehaviorSubject<boolean>(!!token);
    this.isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

    this.pendingPasswordChangeSubject = new BehaviorSubject<boolean>(pendingPasswordChange);
    this.pendingPasswordChange$ = this.pendingPasswordChangeSubject.asObservable();

    // Check current authentication status on init
    this.checkAuthStatus();
  }

  /**
   * Check current authentication status with Cognito
   */
  private async checkAuthStatus(): Promise<void> {
    try {
      const user = await getCurrentUser();
      const session = await fetchAuthSession();
      
      if (session.tokens?.idToken) {
        const cognitoUser: User = {
          id: user.userId,
          username: user.username,
          email: user.signInDetails?.loginId
        };

        const token = session.tokens.idToken.toString();
        
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(this.TOKEN_KEY, token);
          localStorage.setItem(this.USER_KEY, JSON.stringify(cognitoUser));
        }

        this.currentUserSubject.next(cognitoUser);
        this.isAuthenticatedSubject.next(true);
      }
    } catch (error) {
      // User not authenticated
      this.clearSession();
    }
  }

  /**
   * Login user with AWS Cognito
   */
  login(credentials: LoginRequest): Observable<AuthResponse> {
    // First, try to sign out any existing session
    return from(this.signOutIfNeeded()).pipe(
      switchMap(() => 
        from(
          signIn({
            username: credentials.username,
            password: credentials.password,
          })
        )
      ),
      switchMap((result: SignInOutput) => {
        console.log('✅ Cognito sign in result:', result);
        
        // Check if password change is required
        if (result.nextStep.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
          console.log('🔑 Password change required');
          // Set pending password change flag
          this.setPendingPasswordChange(true);
          // Return special response indicating password change needed
          return throwError(() => ({ 
            error: 'PASSWORD_CHANGE_REQUIRED',
            requiresPasswordChange: true 
          }));
        }
        
        // Normal login flow - Get user details and session
        return from(this.getUserDetailsAfterSignIn());
      }),
      catchError((error) => {
        // If this is our password change required error, pass it through
        if (error.requiresPasswordChange) {
          return throwError(() => error);
        }
        
        console.error('❌ Cognito sign in error:', error);
        let errorMessage = 'Error de autenticación';
        
        // Handle common Cognito errors
        switch (error.name) {
          case 'UserNotFoundException':
            errorMessage = 'Usuario no encontrado';
            break;
          case 'NotAuthorizedException':
            errorMessage = 'Usuario o contraseña incorrectos';
            break;
          case 'UserNotConfirmedException':
            errorMessage = 'Usuario no confirmado. Verifica tu email.';
            break;
          case 'PasswordResetRequiredException':
            errorMessage = 'Debes restablecer tu contraseña';
            break;
          case 'TooManyRequestsException':
            errorMessage = 'Demasiados intentos. Intenta más tarde.';
            break;
          case 'InvalidParameterException':
            errorMessage = 'Parámetros inválidos';
            break;
          case 'UserAlreadyAuthenticatedException':
            errorMessage = 'Ya hay una sesión activa. Cerrando sesión previa...';
            break;
          default:
            errorMessage = error.message || 'Error de autenticación';
        }
        
        return throwError(() => ({ error: errorMessage }));
      })
    );
  }

  /**
   * Sign out if there's an existing session
   */
  private async signOutIfNeeded(): Promise<void> {
    try {
      const user = await getCurrentUser();
      if (user) {
        console.log('🔓 Closing existing session...');
        await signOut();
        this.clearSession();
      }
    } catch (error) {
      // No user signed in, continue
    }
  }

  /**
   * Get user details after successful sign in
   */
  private async getUserDetailsAfterSignIn(): Promise<AuthResponse> {
    try {
      const user = await getCurrentUser();
      const session = await fetchAuthSession();
      
      if (!session.tokens?.idToken) {
        throw new Error('No se pudo obtener el token de sesión');
      }

      const cognitoUser: User = {
        id: user.userId,
        username: user.username,
        email: user.signInDetails?.loginId
      };

      const token = session.tokens.idToken.toString();

      const response: AuthResponse = {
        token,
        user: cognitoUser
      };

      // Store session
      this.setSession(response);

      return response;
    } catch (error) {
      console.error('Error getting user details:', error);
      throw error;
    }
  }

  /**
   * Set user session data
   */
  private setSession(response: AuthResponse): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.TOKEN_KEY, response.token);
      localStorage.setItem(this.USER_KEY, JSON.stringify(response.user));
    }

    this.currentUserSubject.next(response.user);
    this.isAuthenticatedSubject.next(true);

    console.log('✅ Session set for user:', response.user.username);
  }

  /**
   * Clear session data
   */
  private clearSession(): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.USER_KEY);
    }

    this.currentUserSubject.next(null);
    this.isAuthenticatedSubject.next(false);
  }

  /**
   * Logout user from Cognito
   */
  logout(): void {
    signOut()
      .then(() => {
        console.log('✅ Signed out from Cognito');
        this.clearSession();
      })
      .catch((error) => {
        console.error('❌ Error signing out:', error);
        // Clear session anyway
        this.clearSession();
      });
  }

  /**
   * Get current user
   */
  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.isAuthenticatedSubject.value;
  }

  /**
   * Get auth token (JWT from Cognito)
   */
  getToken(): string | null {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem(this.TOKEN_KEY);
    }
    return null;
  }

  /**
   * Get fresh auth token from Cognito session
   */
  async getTokenAsync(): Promise<string | null> {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.idToken?.toString() || null;
    } catch (error) {
      console.error('Error getting token:', error);
      return null;
    }
  }

  /**
   * Refresh authentication session
   */
  async refreshSession(): Promise<void> {
    try {
      const session = await fetchAuthSession({ forceRefresh: true });
      
      if (session.tokens?.idToken) {
        const token = session.tokens.idToken.toString();
        
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(this.TOKEN_KEY, token);
        }
        
        this.isAuthenticatedSubject.next(true);
        console.log('✅ Session refreshed');
      } else {
        this.clearSession();
      }
    } catch (error) {
      console.error('❌ Error refreshing session:', error);
      this.clearSession();
    }
  }

  /**
   * Set pending password change flag
   */
  private setPendingPasswordChange(pending: boolean): void {
    if (typeof localStorage !== 'undefined') {
      if (pending) {
        localStorage.setItem(this.PENDING_PASSWORD_CHANGE, 'true');
      } else {
        localStorage.removeItem(this.PENDING_PASSWORD_CHANGE);
      }
    }
    this.pendingPasswordChangeSubject.next(pending);
  }

  /**
   * Check if there's a pending password change
   */
  hasPendingPasswordChange(): boolean {
    return this.pendingPasswordChangeSubject.value;
  }

  /**
   * Complete new password challenge
   */
  completeNewPasswordChallenge(newPassword: string): Observable<AuthResponse> {
    return from(
      confirmSignIn({
        challengeResponse: newPassword
      })
    ).pipe(
      switchMap(() => {
        console.log('✅ Password changed successfully');
        this.setPendingPasswordChange(false);
        // Get user details after password change
        return from(this.getUserDetailsAfterSignIn());
      }),
      catchError((error) => {
        console.error('❌ Error changing password:', error);
        let errorMessage = 'Error al cambiar la contraseña';
        
        if (error.name === 'InvalidPasswordException') {
          errorMessage = 'La contraseña no cumple con los requisitos de seguridad';
        } else if (error.name === 'InvalidParameterException') {
          errorMessage = 'Parámetros inválidos. Verifica que la contraseña cumpla con los requisitos.';
        }
        
        return throwError(() => ({ error: errorMessage }));
      })
    );
  }

  /**
   * Cancel password change and return to login
   */
  cancelPasswordChange(): void {
    this.setPendingPasswordChange(false);
    this.clearSession();
    // Sign out to clear any pending Cognito state
    signOut().catch(error => console.error('Error during sign out:', error));
  }
}

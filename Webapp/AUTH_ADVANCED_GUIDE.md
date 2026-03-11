# Authentication System - Advanced Configuration Guide

## HTTP Interceptor Setup (Optional)

To automatically attach authentication tokens to all HTTP requests, use the provided interceptor.

### Step 1: Add Provider to app.config.ts

```typescript
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors, HTTP_INTERCEPTORS } from '@angular/common/http';
import { AuthInterceptor } from './services/auth.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(),
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
  ]
};
```

### Step 2: How It Works

The interceptor automatically:
1. Adds `Authorization: Bearer <token>` header to all requests
2. Handles 401 errors by logging out the user
3. Redirects to login on token expiration

### Step 3: Usage

No changes needed in components! The interceptor works transparently:

```typescript
// This request will automatically include the auth token
this.http.post('/api/data', payload).subscribe(
  response => console.log(response),
  error => console.error(error)
);
```

## Role-Based Access Control (RBAC)

### Create Role Guard

```typescript
// src/app/services/role.guard.ts
import { Injectable } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { inject } from '@angular/core';

export const roleGuard = (requiredRole: string): CanActivateFn => {
  return (route, state) => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const user = authService.getCurrentUser();

    if (user && (user as any).role === requiredRole) {
      return true;
    }

    router.navigate(['/unauthorized']);
    return false;
  };
};
```

### Use in Routes

```typescript
// app.routes.ts
{
  path: 'admin',
  component: AdminComponent,
  canActivate: [roleGuard('admin')]
}
```

## Token Refresh Implementation

### Update Auth Service

```typescript
// Add to auth.service.ts
refreshToken(): Observable<AuthResponse> {
  const refreshToken = localStorage.getItem('refresh_token');
  return this.http.post<AuthResponse>('/api/auth/refresh', { 
    refreshToken 
  }).pipe(
    tap(response => this.setSession(response)),
    catchError(() => {
      this.logout();
      return throwError(() => new Error('Token refresh failed'));
    })
  );
}
```

### Use in Interceptor

```typescript
// In auth.interceptor.ts
if (error.status === 401) {
  return this.authService.refreshToken().pipe(
    switchMap(response => {
      const clonedRequest = request.clone({
        setHeaders: {
          Authorization: `Bearer ${response.token}`
        }
      });
      return next.handle(clonedRequest);
    }),
    catchError(() => {
      this.authService.logout();
      this.router.navigate(['/login']);
      return throwError(() => error);
    })
  );
}
```

## Secure Token Storage (Advanced)

For production, consider storing tokens in httpOnly cookies instead of localStorage:

```typescript
// Backend should set httpOnly cookie with token
// Frontend automatically includes it in requests
// No XSS vulnerability with localStorage

// HttpClient automatically sends cookies with requests
// No need to manually add Authorization header
```

## Two-Factor Authentication (2FA)

### Add 2FA Check

```typescript
// Update auth.service.ts
export interface LoginResponse {
  token?: string;
  user?: User;
  requiresOTP?: boolean;
}

verify2FA(otp: string): Observable<AuthResponse> {
  return this.http.post<AuthResponse>('/api/auth/verify-otp', { otp });
}
```

### Create 2FA Component

```typescript
// src/app/components/otp-verify/otp-verify.ts
@Component({
  selector: 'app-otp-verify',
  template: `
    <div class="otp-form">
      <h2>Enter OTP</h2>
      <input type="text" [(ngModel)]="otp" placeholder="Enter 6-digit OTP">
      <button (click)="verify()">Verify</button>
    </div>
  `
})
export class OTPVerifyComponent {
  otp: string = '';
  
  verify() {
    // Call authService.verify2FA()
  }
}
```

## Session Timeout

### Add Auto-Logout on Inactivity

```typescript
// src/app/services/session-timeout.service.ts
@Injectable({ providedIn: 'root' })
export class SessionTimeoutService {
  private timeout: any;
  private TIMEOUT_DURATION = 15 * 60 * 1000; // 15 minutes

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  startTimer() {
    this.resetTimer();
    
    document.addEventListener('mousemove', () => this.resetTimer());
    document.addEventListener('keydown', () => this.resetTimer());
  }

  private resetTimer() {
    clearTimeout(this.timeout);
    this.timeout = setTimeout(() => {
      this.authService.logout();
      this.router.navigate(['/login']);
    }, this.TIMEOUT_DURATION);
  }
}
```

### Use in App Component

```typescript
export class ChatContainerComponent implements OnInit {
  constructor(private sessionTimeout: SessionTimeoutService) {}

  ngOnInit() {
    this.sessionTimeout.startTimer();
  }
}
```

## Logout All Devices

```typescript
// Add to auth.service.ts
logoutAllDevices(): Observable<any> {
  return this.http.post('/api/auth/logout-all', {}).pipe(
    tap(() => {
      this.logout();
    })
  );
}
```

## Testing Authentication

### Unit Test Example

```typescript
// src/app/services/auth.service.spec.ts
describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('should login successfully', () => {
    const mockResponse = {
      token: 'test_token',
      user: { id: '1', username: 'test' }
    };

    service.login({ username: 'test', password: 'password' })
      .subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

    const req = httpMock.expectOne('/api/auth/login');
    expect(req.request.method).toBe('POST');
    req.flush(mockResponse);
  });

  afterEach(() => {
    httpMock.verify();
  });
});
```

## Security Best Practices

1. **Use HTTPS only** - Never transmit tokens over HTTP
2. **Short-lived tokens** - Use JWT with short expiration (15-60 min)
3. **Refresh tokens** - Use longer-lived refresh tokens
4. **HttpOnly cookies** - Store tokens in httpOnly cookies if possible
5. **CSRF protection** - Implement CSRF tokens for state-changing operations
6. **Input validation** - Always validate credentials on both client and server
7. **Rate limiting** - Implement rate limiting on login endpoint
8. **Logging** - Log authentication events for security auditing

## Common Issues & Solutions

### Token Expires Mid-Request
**Solution**: Implement token refresh in interceptor

### User Logged Out on Page Refresh
**Solution**: AuthService auto-recovers from localStorage on init

### CORS Errors with API
**Solution**: Enable CORS on backend, include credentials in requests

```typescript
this.http.post(url, data, { withCredentials: true })
```

### 401 Loop After Token Refresh
**Solution**: Ensure refresh endpoint doesn't require auth header

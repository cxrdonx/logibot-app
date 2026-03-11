import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);

  loginForm: FormGroup;
  submitted = false;
  loading = false;
  error: string | null = null;
  returnUrl: string = '';
  showPassword = false;

  constructor() {
    this.loginForm = this.fb.group({
      username: ['', [Validators.required, Validators.minLength(3)]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  ngOnInit() {
    // Get return URL from route parameters or default to '/'
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
    
    // Check if user is already authenticated
    this.authService.isAuthenticated$.subscribe(isAuth => {
      if (isAuth) {
        console.log('✅ User already authenticated, redirecting...');
        this.router.navigateByUrl(this.returnUrl);
      }
    });
  }

  get f() {
    return this.loginForm.controls;
  }

  onSubmit() {
    this.submitted = true;
    this.error = null;

    // Stop if form is invalid
    if (this.loginForm.invalid) {
      return;
    }

    this.loading = true;
    // Disable form controls while loading (best practice for reactive forms)
    this.loginForm.disable();

    this.authService.login({
      username: this.f['username'].value,
      password: this.f['password'].value
    }).subscribe({
      next: (response) => {
        this.loading = false;
        this.loginForm.enable();
        // Navigate to return URL or dashboard
        this.router.navigateByUrl(this.returnUrl);
      },
      error: (error) => {
        this.loading = false;
        this.loginForm.enable();
        
        // Check if password change is required
        if (error.requiresPasswordChange) {
          console.log('🔑 Redirecting to password change...');
          this.router.navigate(['/change-password']);
          return;
        }
        
        this.error = error?.error || 'Usuario o contraseña incorrectos, intente nuevamente.';
      }
    });
  }

  togglePasswordVisibility() {
    this.showPassword = !this.showPassword;
  } 
}

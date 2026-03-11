import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './change-password.html',
  styleUrls: ['./change-password.css']
})
export class ChangePasswordComponent {
  private authService = inject(AuthService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  changePasswordForm: FormGroup;
  submitted = false;
  loading = false;
  error: string | null = null;
  showPassword = false;
  showConfirmPassword = false;

  constructor() {
    this.changePasswordForm = this.fb.group({
      newPassword: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]]
    }, { validators: this.passwordMatchValidator });

    // Redirect if no pending password change
    if (!this.authService.hasPendingPasswordChange()) {
      this.router.navigate(['/login']);
    }
  }

  get f() {
    return this.changePasswordForm.controls;
  }

  passwordMatchValidator(form: FormGroup) {
    const password = form.get('newPassword');
    const confirmPassword = form.get('confirmPassword');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    
    return null;
  }

  onSubmit() {
    this.submitted = true;
    this.error = null;

    if (this.changePasswordForm.invalid) {
      return;
    }

    this.loading = true;
    this.changePasswordForm.disable();

    this.authService.completeNewPasswordChallenge(this.f['newPassword'].value)
      .subscribe({
        next: () => {
          this.loading = false;
          this.changePasswordForm.enable();
          // Navigate to main app
          this.router.navigate(['/']);
        },
        error: (error) => {
          this.loading = false;
          this.changePasswordForm.enable();
          this.error = error?.error || 'Error al cambiar la contraseña. Intente nuevamente.';
        }
      });
  }

  togglePasswordVisibility(field: 'password' | 'confirm') {
    if (field === 'password') {
      this.showPassword = !this.showPassword;
    } else {
      this.showConfirmPassword = !this.showConfirmPassword;
    }
  }

  cancel() {
    this.authService.cancelPasswordChange();
    this.router.navigate(['/login']);
  }
}

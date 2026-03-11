import {
  Component,
  OnInit,
  OnDestroy,
  inject,
  PLATFORM_ID,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
  AfterViewChecked
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { HeaderComponent } from '../header/header';
import { AuthService } from '../../services/auth.service';
import { ChatbotMessage } from '../../models/types';

interface MaritimeMessage {
  id: number;
  sender: 'bot' | 'user';
  text: string;
  timestamp: Date;
  isError?: boolean;
}

interface MaritimeChatbotRequest {
  query: string;
  conversation_history?: ChatbotMessage[];
}

interface MaritimeChatbotResponse {
  respuesta: string;
  items_found?: number;
}

@Component({
  selector: 'app-chat-maritimo',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './chat-maritimo.html',
  styleUrls: ['./chat-maritimo.css']
})
export class ChatMaritimoComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('scrollEnd') private scrollEnd!: ElementRef;

  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private cdr = inject(ChangeDetectorRef);
  private authService = inject(AuthService);
  private router = inject(Router);

  private readonly API_URL =
    'https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod/chatbot-maritimo';
  private readonly MAX_HISTORY_MESSAGES = 10;
  private conversationHistory: ChatbotMessage[] = [];
  private activeTypingIntervals: number[] = [];

  messages: MaritimeMessage[] = [];
  isTyping = false;
  inputText = '';
  today: Date = new Date();

  ngOnInit(): void {
    this.loadConversationFromStorage();
    if (this.messages.length === 0) {
      setTimeout(() => {
        this.addBotMessageWithTypingEffect(
          'Hola. Soy ALCE, tu experto en logística marítima.\n\n' +
          'Puedo ayudarte con cotizaciones marítimas, rutas de contenedores, ' +
          'navieras y términos de embarque.\n\n' +
          'Ejemplo: "¿Cuánto cuesta un contenedor 40HC de Rotterdam a Puerto Barrios?"'
        );
      }, 400);
    }
  }

  ngOnDestroy(): void {
    this.saveConversationToStorage();
    this.activeTypingIntervals.forEach((id) => clearInterval(id));
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.scrollEnd?.nativeElement.scrollIntoView({ behavior: 'smooth' });
    } catch {
      // silent
    }
  }

  sendMessage(): void {
    const text = this.inputText.trim();
    if (!text || this.isTyping) return;

    this.inputText = '';
    this.messages.push({
      id: Date.now(),
      sender: 'user',
      text,
      timestamp: new Date()
    });

    this.isTyping = true;
    this.cdr.detectChanges();

    const request: MaritimeChatbotRequest = {
      query: text,
      conversation_history: this.conversationHistory.slice(-this.MAX_HISTORY_MESSAGES)
    };

    this.http.post<MaritimeChatbotResponse>(this.API_URL, request).subscribe({
      next: (response) => {
        this.isTyping = false;
        this.addBotMessageWithTypingEffect(response.respuesta);

        this.conversationHistory.push(
          { role: 'user', content: [{ text }] },
          { role: 'assistant', content: [{ text: response.respuesta }] }
        );

        this.saveConversationToStorage();
      },
      error: (err: HttpErrorResponse) => {
        this.isTyping = false;

        let errorMsg = 'Error conectando con el servidor.';
        if (err.status === 400) {
          errorMsg = err.error?.error ?? 'Solicitud inválida.';
        } else if (err.status === 500) {
          errorMsg = err.error?.error ?? 'Error interno del servidor.';
        } else if (err.status === 404) {
          errorMsg = 'Endpoint no encontrado. Verifica la URL.';
        } else if (err.status === 0) {
          errorMsg = 'Error de red o CORS.';
        }

        this.messages.push({
          id: Date.now(),
          sender: 'bot',
          text: errorMsg,
          timestamp: new Date(),
          isError: true
        });
        this.cdr.detectChanges();
      }
    });
  }

  resetConversation(): void {
    this.activeTypingIntervals.forEach((id) => clearInterval(id));
    this.activeTypingIntervals = [];
    this.messages = [];
    this.conversationHistory = [];
    this.saveConversationToStorage();

    setTimeout(() => {
      this.addBotMessageWithTypingEffect(
        'Hola. Soy ALCE, tu experto en logística marítima.\n\n' +
        'Puedo ayudarte con cotizaciones marítimas, rutas de contenedores, ' +
        'navieras y términos de embarque.\n\n' +
        'Ejemplo: "¿Cuánto cuesta un contenedor 40HC de Rotterdam a Puerto Barrios?"'
      );
    }, 400);
  }

  handleLogout(): void {
    this.saveConversationToStorage();
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  private addBotMessageWithTypingEffect(fullText: string): void {
    const msgId = Date.now();
    const botMessage: MaritimeMessage = {
      id: msgId,
      sender: 'bot',
      text: '',
      timestamp: new Date()
    };

    this.messages.push(botMessage);
    this.cdr.detectChanges();

    let currentIndex = 0;
    const typingSpeed = 12;

    const intervalId = setInterval(() => {
      if (currentIndex < fullText.length) {
        const idx = this.messages.findIndex((m) => m.id === msgId);
        if (idx !== -1) {
          this.messages[idx].text = fullText.substring(0, currentIndex + 1);
          this.cdr.detectChanges();
        }
        currentIndex++;
      } else {
        clearInterval(intervalId);
        const pos = this.activeTypingIntervals.indexOf(intervalId as unknown as number);
        if (pos > -1) {
          this.activeTypingIntervals.splice(pos, 1);
        }
        this.saveConversationToStorage();
      }
    }, typingSpeed) as unknown as number;

    this.activeTypingIntervals.push(intervalId);
  }

  private saveConversationToStorage(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      localStorage.setItem('alce_maritimo_messages', JSON.stringify(this.messages));
      localStorage.setItem(
        'alce_maritimo_history',
        JSON.stringify(this.conversationHistory)
      );
    } catch {
      // silent
    }
  }

  private loadConversationFromStorage(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      const savedMessages = localStorage.getItem('alce_maritimo_messages');
      const savedHistory = localStorage.getItem('alce_maritimo_history');

      if (savedMessages) {
        this.messages = JSON.parse(savedMessages).map((m: MaritimeMessage) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }));
      }
      if (savedHistory) {
        this.conversationHistory = JSON.parse(savedHistory);
      }
    } catch {
      this.messages = [];
      this.conversationHistory = [];
    }
  }
}

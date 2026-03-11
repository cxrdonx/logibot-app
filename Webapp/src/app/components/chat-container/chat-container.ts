import { Component, OnInit, OnDestroy, inject, PLATFORM_ID, ChangeDetectorRef } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpErrorResponse, HttpClientModule } from '@angular/common/http';
import { Router } from '@angular/router';

// Importamos los componentes hijos
import { HeaderComponent } from '../header/header';
import { ChatComponent } from '../chat/chat';
import { FooterComponent } from '../footer/footer';
import { Message, ChatbotMessage, ChatbotRequest, ChatbotResponse, Conversation, XMLQuotation } from '../../models/types';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-chat-container',
  standalone: true,
  imports: [CommonModule, HttpClientModule, HeaderComponent, ChatComponent, FooterComponent],
  template: `
    <div class="flex flex-col h-screen bg-slate-50 font-sans w-full">
      <!-- HEADER FIJO -->
      <app-header
        [isOnline]="isOnline"
        [conversations]="conversations"
        [currentConversationId]="currentConversationId"
        (onReset)="resetCurrentConversation()"
        (onNewConversation)="createNewConversation()"
        (onSelectConversation)="switchConversation($event)"
        (onDeleteConversation)="deleteConversation($event)"
        (onLogout)="handleLogout()">
      </app-header>

      <!-- CHAT (BODY) - CON SCROLL -->
      <div class="flex-1 overflow-hidden">
        <app-chat
          [messages]="messages"
          [isTyping]="isTyping">
        </app-chat>
      </div>

      <!-- FOOTER FIJO (INPUT) -->
      <app-footer
        [isDisabled]="isTyping || !isOnline"
        (onSendMessage)="handleUserMessage($event)">
      </app-footer>
    </div>
  `
})
export class ChatContainerComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private cdr = inject(ChangeDetectorRef);
  private authService = inject(AuthService);
  private router = inject(Router);
  
  // API URL para Chatbot V2
  private readonly API_URL = 'https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod/chatbot';
  
  // Historial conversacional para enviar al API
  private conversationHistory: ChatbotMessage[] = [];
  
  // Límite de mensajes para enviar al backend (últimos 10 mensajes)
  private readonly MAX_HISTORY_MESSAGES = 10;
  
  // Control del efecto de typing
  private activeTypingIntervals: number[] = [];

  // Gestión de conversaciones
  conversations: Conversation[] = [];
  currentConversationId: string = '';

  messages: Message[] = [];
  isTyping: boolean = false;
  isOnline: boolean = true;

  ngOnInit() {
    // Cargar conversaciones desde localStorage
    this.loadConversations();
    
    // Si no hay conversaciones, crear la primera
    if (this.conversations.length === 0) {
      this.createNewConversation();
    } else {
      // Cargar la última conversación activa
      this.loadConversation(this.currentConversationId);
    }
  }
  
  ngOnDestroy() {
    // Guardar conversación actual antes de destruir
    this.saveCurrentConversation();
    // Limpiar todos los intervalos activos
    this.activeTypingIntervals.forEach(interval => clearInterval(interval));
  }

  createNewConversation() {
    const newConv: Conversation = {
      id: this.generateId(),
      name: 'Nueva conversación', // Temporal, se actualizará con el primer mensaje
      createdAt: new Date(),
      updatedAt: new Date(),
      messages: [],
      conversationHistory: []
    };
    
    // Guardar conversación actual antes de cambiar
    this.saveCurrentConversation();
    
    this.conversations.unshift(newConv);
    this.currentConversationId = newConv.id;
    this.messages = [];
    this.conversationHistory = [];
    
    // Limpiar intervalos activos
    this.activeTypingIntervals.forEach(interval => clearInterval(interval));
    this.activeTypingIntervals = [];
    
    // Mensaje de bienvenida
    setTimeout(() => {
      this.addBotMessageWithTypingEffect('👋 Hola. Soy LogiBot AI.\n\nPuedo ayudarte con consultas sobre tarifas de logística.\n\nEjemplo: "¿Cuánto cuesta enviar 26,000 kg de Puerto Quetzal a Mixco?"');
    }, 500);
    
    this.saveConversations();
  }

  switchConversation(conversationId: string) {
    if (conversationId === this.currentConversationId) return;
    
    // Guardar conversación actual
    this.saveCurrentConversation();
    
    // Cargar nueva conversación
    this.loadConversation(conversationId);
  }

  deleteConversation(conversationId: string) {
    const index = this.conversations.findIndex(c => c.id === conversationId);
    if (index === -1) return;
    
    this.conversations.splice(index, 1);
    
    // Si eliminamos la conversación actual
    if (conversationId === this.currentConversationId) {
      if (this.conversations.length > 0) {
        this.loadConversation(this.conversations[0].id);
      } else {
        this.createNewConversation();
      }
    }
    
    this.saveConversations();
  }

  resetCurrentConversation() {
    // Limpiar todos los intervalos de typing activos
    this.activeTypingIntervals.forEach(interval => clearInterval(interval));
    this.activeTypingIntervals = [];
    
    this.messages = [];
    this.conversationHistory = [];
    
    // Actualizar conversación actual
    const currentConv = this.conversations.find(c => c.id === this.currentConversationId);
    if (currentConv) {
      currentConv.messages = [];
      currentConv.conversationHistory = [];
      currentConv.updatedAt = new Date();
    }
    
    this.saveConversations();
    
    // Mensaje de bienvenida
    setTimeout(() => {
      this.addBotMessageWithTypingEffect('👋 Hola. Soy LogiBot AI.\n\nPuedo ayudarte con consultas sobre tarifas de logística.\n\nEjemplo: "¿Cuánto cuesta enviar 26,000 kg de Puerto Quetzal a Mixco?"');
    }, 500);
  }

  handleUserMessage(text: string) {
    console.log('📤 Usuario envió mensaje:', text);
    
    // Agregar mensaje del usuario a la UI
    this.messages.push({
      id: Date.now(),
      sender: 'user',
      text: text,
      type: 'text',
      timestamp: new Date()
    });
    
    // Actualizar nombre de la conversación si es el primer mensaje del usuario
    const currentConv = this.conversations.find(c => c.id === this.currentConversationId);
    if (currentConv && currentConv.name === 'Nueva conversación') {
      // Usar los primeros 50 caracteres del mensaje como título
      currentConv.name = text.length > 50 ? text.substring(0, 50) + '...' : text;
      this.saveConversations();
    }
    
    this.isTyping = true;

    // Preparar el request según la documentación del Chatbot V2
    const request: ChatbotRequest = {
      query: text,
      conversation_history: this.getRecentHistory()
    };

    console.log('📡 Enviando request al API:', this.API_URL);

    this.http.post<ChatbotResponse>(this.API_URL, request)
      .subscribe({
        next: (response) => {
          console.log('📥 Response recibida del API:', response);
          this.isTyping = false;
          
          // Agregar respuesta del bot a la UI con efecto de typing
          this.addBotMessageWithTypingEffect(response.respuesta);
          
          // Actualizar historial conversacional
          this.conversationHistory.push({
            role: 'user',
            content: [{ text: text }]
          });
          
          this.conversationHistory.push({
            role: 'assistant',
            content: [{ text: response.respuesta }]
          });
          
          // Limitar tamaño del historial
          this.limitHistorySize();
          
          // Guardar conversación actual
          this.saveCurrentConversation();
        },
        error: (err: HttpErrorResponse) => {
          console.error('❌ Error en la llamada al API:', err);
          this.isTyping = false;
          
          let errorMsg = 'Error conectando con el servidor.';
          
          if (err.status === 400) {
            errorMsg = err.error?.error || 'Solicitud inválida.';
          } else if (err.status === 500) {
            errorMsg = err.error?.error || 'Error interno del servidor.';
          } else if (err.status === 404) {
            errorMsg = 'Endpoint no encontrado. Verifica la URL.';
          } else if (err.status === 0) {
            errorMsg = 'Error de red o CORS.';
          }

          this.messages.push({
            id: Date.now(),
            sender: 'bot',
            text: `❌ ${errorMsg}`,
            type: 'text',
            timestamp: new Date(),
            isError: true
          });
        }
      });
  }
  
  /**
   * Detecta si el texto contiene XML y lo parsea
   */
  private parseXMLResponse(text: string): XMLQuotation | null {
    // Verificar si el texto contiene XML
    if (!text.includes('<respuesta>') || !text.includes('<cotizacion>')) {
      return null;
    }

    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(text, 'text/xml');

      // Verificar errores de parseo
      const parserError = xmlDoc.querySelector('parsererror');
      if (parserError) {
        console.error('Error parseando XML:', parserError);
        return null;
      }

      const cotizacion = xmlDoc.querySelector('cotizacion');
      if (!cotizacion) return null;

      // Función helper para obtener texto de un elemento
      const getText = (parent: Element, selector: string): string => {
        return parent.querySelector(selector)?.textContent?.trim() || '';
      };

      // Función helper para obtener número
      const getNumber = (parent: Element, selector: string): number => {
        const text = getText(parent, selector);
        return parseFloat(text) || 0;
      };

      // Función helper para obtener boolean
      const getBoolean = (parent: Element, selector: string): boolean => {
        const text = getText(parent, selector).toLowerCase();
        return text === 'true' || text === '1';
      };

      // Parsear costos adicionales
      const costosAdicionales: Array<{
        concepto: string;
        valor: number | string;
        unidad: string;
        descripcion: string;
      }> = [];

      xmlDoc.querySelectorAll('costos_adicionales > costo').forEach(costo => {
        const valorText = getText(costo, 'valor');
        const valor = isNaN(parseFloat(valorText)) ? valorText : parseFloat(valorText);
        
        costosAdicionales.push({
          concepto: getText(costo, 'concepto'),
          valor: valor,
          unidad: getText(costo, 'unidad'),
          descripcion: getText(costo, 'descripcion')
        });
      });

      // Parsear custodio (opcional)
      const custodioElement = xmlDoc.querySelector('custodio');
      const custodio = custodioElement ? {
        tipo: getText(custodioElement, 'tipo'),
        costo_unitario: getNumber(custodioElement, 'costo_unitario'),
        cantidad_unidades: getNumber(custodioElement, 'cantidad_unidades'),
        costo_total: getNumber(custodioElement, 'costo_total'),
        moneda: getText(custodioElement, 'moneda'),
        descripcion: getText(custodioElement, 'descripcion')
      } : undefined;

      const quotation: XMLQuotation = {
        proveedor: getText(cotizacion, 'proveedor'),
        ruta: {
          origen: getText(cotizacion, 'ruta > origen'),
          destino: getText(cotizacion, 'ruta > destino')
        },
        unidad: {
          tipo: getText(cotizacion, 'unidad > tipo'),
          peso_solicitado: getNumber(cotizacion, 'unidad > peso_solicitado'),
          peso_unidad: getText(cotizacion, 'unidad > peso_unidad')
        },
        tarifa_base: {
          monto: getNumber(cotizacion, 'tarifa_base > monto'),
          moneda: getText(cotizacion, 'tarifa_base > moneda'),
          rango: getText(cotizacion, 'tarifa_base > rango')
        },
        sobrepeso: {
          aplica: getBoolean(cotizacion, 'sobrepeso > aplica'),
          monto: getNumber(cotizacion, 'sobrepeso > monto'),
          moneda: getText(cotizacion, 'sobrepeso > moneda'),
          descripcion: getText(cotizacion, 'sobrepeso > descripcion')
        },
        custodio: custodio,
        costos_adicionales: costosAdicionales,
        resumen_costos: {
          subtotal: getNumber(cotizacion, 'resumen_costos > subtotal'),
          total: getNumber(cotizacion, 'resumen_costos > total'),
          moneda: getText(cotizacion, 'resumen_costos > moneda'),
          detalles: getText(cotizacion, 'resumen_costos > detalles'),
          condiciones_aduana: getText(cotizacion, 'resumen_costos > condiciones_aduana'),
          condiciones_cominter: getText(cotizacion, 'resumen_costos > condiciones_cominter'),
          descripcion: getText(cotizacion, 'resumen_costos > descripcion'),
          nota: getText(cotizacion, 'resumen_costos > nota')
        }
      };

      return quotation;
    } catch (error) {
      console.error('Error parseando XML:', error);
      return null;
    }
  }

  /**
   * Agrega un mensaje del bot con efecto de escritura letra por letra
   */
  private addBotMessageWithTypingEffect(fullText: string): void {
    console.log('🔵 Iniciando typing effect para:', fullText.substring(0, 50) + '...');
    
    const botMessageId = Date.now();
    
    // Detectar si es una cotización XML
    const xmlQuotation = this.parseXMLResponse(fullText);
    
    if (xmlQuotation) {
      // Si es XML, crear mensaje con tipo 'xml-quotation' sin efecto de typing
      console.log('📋 Cotización XML detectada');
      const botMessage: Message = {
        id: botMessageId,
        sender: 'bot',
        type: 'xml-quotation',
        data: xmlQuotation,
        timestamp: new Date()
      };
      
      this.messages.push(botMessage);
      this.cdr.detectChanges();
      
      // Guardar conversación
      this.saveCurrentConversation();
      return;
    }
    
    // Si no es XML, continuar con el efecto de typing normal
    // Crear mensaje inicial vacío
    const botMessage: Message = {
      id: botMessageId,
      sender: 'bot',
      text: '',
      type: 'text',
      timestamp: new Date()
    };
    
    this.messages.push(botMessage);
    console.log('✅ Mensaje vacío agregado. Total mensajes:', this.messages.length);
    
    // Forzar detección de cambios
    this.cdr.detectChanges();
    
    // Efecto de typing letra por letra
    let currentIndex = 0;
    const typingSpeed = 15; // milisegundos por letra (ajusta para más rápido/lento)
    
    const typingInterval = setInterval(() => {
      if (currentIndex < fullText.length) {
        // Actualizar el texto del mensaje
        const messageIndex = this.messages.findIndex(m => m.id === botMessageId);
        if (messageIndex !== -1) {
          this.messages[messageIndex].text = fullText.substring(0, currentIndex + 1);
          // Forzar detección de cambios en cada iteración
          this.cdr.detectChanges();
        }
        currentIndex++;
      } else {
        // Terminar el efecto
        console.log('✅ Typing effect completado');
        clearInterval(typingInterval);
        
        // Remover de la lista de intervalos activos
        const index = this.activeTypingIntervals.indexOf(typingInterval as any);
        if (index > -1) {
          this.activeTypingIntervals.splice(index, 1);
        }
        
        // Guardar conversación cuando termine el efecto
        this.saveCurrentConversation();
      }
    }, typingSpeed) as any;
    
    // Guardar referencia del intervalo para limpiarlo si es necesario
    this.activeTypingIntervals.push(typingInterval);
  }
  
  /**
   * Obtiene los mensajes más recientes del historial
   */
  private getRecentHistory(): ChatbotMessage[] {
    return this.conversationHistory.slice(-this.MAX_HISTORY_MESSAGES);
  }
  
  /**
   * Limita el tamaño del historial para no exceder el límite
   */
  private limitHistorySize(): void {
    // No limitamos el historial completo, solo lo que enviamos al backend
    // El historial completo se mantiene para la UI
  }

  // ========== Métodos para gestión de conversaciones ==========
  
  private generateId(): string {
    return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private loadConversations(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    
    try {
      const saved = localStorage.getItem('logibot_conversations');
      const savedCurrentId = localStorage.getItem('logibot_current_conversation_id');
      
      if (saved) {
        this.conversations = JSON.parse(saved).map((conv: any) => ({
          ...conv,
          createdAt: new Date(conv.createdAt),
          updatedAt: new Date(conv.updatedAt),
          messages: conv.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
      }
      
      if (savedCurrentId && this.conversations.find(c => c.id === savedCurrentId)) {
        this.currentConversationId = savedCurrentId;
      } else if (this.conversations.length > 0) {
        this.currentConversationId = this.conversations[0].id;
      }
    } catch (error) {
      console.error('Error cargando conversaciones:', error);
      this.conversations = [];
    }
  }

  private saveConversations(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    
    try {
      localStorage.setItem('logibot_conversations', JSON.stringify(this.conversations));
      localStorage.setItem('logibot_current_conversation_id', this.currentConversationId);
    } catch (error) {
      console.error('Error guardando conversaciones:', error);
    }
  }

  private loadConversation(conversationId: string): void {
    const conv = this.conversations.find(c => c.id === conversationId);
    if (!conv) return;
    
    // Limpiar intervalos de typing
    this.activeTypingIntervals.forEach(interval => clearInterval(interval));
    this.activeTypingIntervals = [];
    
    this.currentConversationId = conversationId;
    this.messages = [...conv.messages];
    this.conversationHistory = [...conv.conversationHistory];
    
    this.saveConversations();
  }

  private saveCurrentConversation(): void {
    if (!this.currentConversationId) return;
    
    const conv = this.conversations.find(c => c.id === this.currentConversationId);
    if (!conv) return;
    
    conv.messages = [...this.messages];
    conv.conversationHistory = [...this.conversationHistory];
    conv.updatedAt = new Date();
    
    this.saveConversations();
  }

  handleLogout(): void {
    // Guardar conversación actual antes de logout
    this.saveCurrentConversation();
    // Ejecutar logout
    this.authService.logout();
    // Redirigir a login
    this.router.navigate(['/login']);
  }
}

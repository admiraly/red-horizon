; Linux SysV ABI. Recorded PCM is signed16 little-endian mono 48000 Hz.
; Fixed preload storage, 128 rotating voices, no hot-path allocation/file loading.
default rel
%define MAX_SAMPLES 192000
%define VOICES 128
%define BLOCK 800
extern snd_pcm_open, snd_pcm_set_params, snd_pcm_writei, snd_pcm_close
extern snd_pcm_avail_update, snd_pcm_recover, getenv
section .rodata
sample_path: db 'content/audio/rifle.pcm',0
device_env: db 'RH_AUDIO_DEVICE',0
default_device: db 'default',0
section .bss align=16
samples: resb MAX_SAMPLES*2+2
sample_count: resq 1
positions: resd VOICES
next_voice: resd 1
pcm: resq 1
pending: resq 1
pending_offset: resq 1
mix_buffer: resw BLOCK
section .text
global audio_init, audio_shot, audio_update, audio_shutdown
global audio_load, audio_mix, audio_active
; audio_load(RDI=path) -> EAX 0 success / 1 invalid/unreadable.
; Preload only, calls prohibited while mixer executes. Invalid load disables shots.
audio_load:
    mov qword [sample_count],0
    mov qword [pending],0
    mov eax,2
    xor esi,esi
    xor edx,edx
    syscall
    test rax,rax
    js .bad
    mov r8,rax
    xor r9d,r9d
.read:
    xor eax,eax
    mov rdi,r8
    lea rsi,[samples]
    add rsi,r9
    mov edx,MAX_SAMPLES*2+2
    sub rdx,r9
    syscall
    test rax,rax
    js .read_bad
    jz .eof
    add r9,rax
    cmp r9,MAX_SAMPLES*2
    ja .read_bad
    jmp .read
.eof:
    mov eax,3
    mov rdi,r8
    syscall
    test r9,r9
    jz .bad
    test r9b,1
    jnz .bad
    shr r9,1
    mov [sample_count],r9
    lea rdi,[positions]
    mov eax,-1
    mov ecx,VOICES
    rep stosd
    mov dword [next_voice],0
    xor eax,eax
    ret
.read_bad:
    mov eax,3
    mov rdi,r8
    syscall
.bad:
    mov eax,1
    ret
; audio_init() -> EAX 0 ready, 1 invalid content, 2 unavailable device.
; Call once before frame loop. Repeated init requires shutdown first.
audio_init:
    push rbp
    mov rbp,rsp
    push r12
    sub rsp,24
    lea rdi,[sample_path]
    call audio_load
    test eax,eax
    jnz .done
    lea rdi,[device_env]
    call getenv wrt ..plt
    test rax,rax
    jnz .name
    lea rax,[default_device]
.name:
    mov rsi,rax
    lea rdi,[pcm]
    xor edx,edx ; playback
    mov ecx,1 ; NONBLOCK
    call snd_pcm_open wrt ..plt
    test eax,eax
    js .unavailable
    mov rdi,[pcm]
    mov esi,2 ; SND_PCM_FORMAT_S16_LE
    mov edx,3 ; SND_PCM_ACCESS_RW_INTERLEAVED
    mov ecx,1
    mov r8d,48000
    mov r9d,1
    mov qword [rsp],40000 ; latency usec, seventh argument
    call snd_pcm_set_params wrt ..plt
    test eax,eax
    js .close_failed
    xor eax,eax
    jmp .done
.close_failed:
    mov rdi,[pcm]
    call snd_pcm_close wrt ..plt
.unavailable:
    mov qword [pcm],0
    mov eax,2
.done:
    add rsp,24
    pop r12
    pop rbp
    ret
; audio_shot() -> void; sequential frame-thread access only.
; Voice pool saturation replaces oldest submitted shot by rotating slot.
audio_shot:
    cmp qword [sample_count],0
    je .done
    mov eax,[next_voice]
    lea rdx,[positions]
    mov dword [rdx+rax*4],0
    inc eax
    and eax,VOICES-1
    mov [next_voice],eax
.done:
    ret
; audio_mix(RDI=output int16*, RSI=frames 0..800) -> EAX frames / -1 bound.
; Caller provides writable frames*2 bytes. Signed32 accumulation, signed16 clamp.
; Clobbers volatile registers only. No allocation, libc, file or device calls.
audio_mix:
    cmp rsi,BLOCK
    ja .bad
    mov r11d,esi
    test rsi,rsi
    jz .done
    lea r8,[positions]
    lea r9,[samples]
    xor ecx,ecx
.frame:
    xor edx,edx
    xor r10d,r10d
.voice:
    mov eax,[r8+r10*4]
    test eax,eax
    js .next
    cmp rax,[sample_count]
    jae .retire
    movsx eax,word [r9+rax*2]
    add edx,eax
    inc dword [r8+r10*4]
    jmp .next
.retire:
    mov dword [r8+r10*4],-1
.next:
    inc r10d
    cmp r10d,VOICES
    jb .voice
    cmp edx,32767
    jle .low
    mov edx,32767
.low:
    cmp edx,-32768
    jge .store
    mov edx,-32768
.store:
    mov [rdi+rcx*2],dx
    inc rcx
    cmp rcx,rsi
    jb .frame
.done:
    mov eax,r11d
    ret
.bad:
    mov eax,-1
    ret
; audio_active() -> EAX count voices with remaining samples, for diagnostics.
audio_active:
    lea rdx,[positions]
    xor eax,eax
    xor ecx,ecx
.loop:
    mov esi,[rdx+rcx*4]
    test esi,esi
    js .next
    cmp rsi,[sample_count]
    jae .next
    inc eax
.next:
    inc ecx
    cmp ecx,VOICES
    jb .loop
    ret
; audio_update() -> void. Nonblocking single-thread pump; <=800 fresh frames.
; Retains partial writes/EAGAIN data. ALSA recovery resets device on underrun.
audio_update:
    cmp qword [pcm],0
    je .return
    push rbp
    mov rbp,rsp
    cmp qword [pending],0
    jne .write
    mov rdi,[pcm]
    call snd_pcm_avail_update wrt ..plt
    test rax,rax
    js .recover
    jz .done
    cmp rax,BLOCK
    jbe .mix
    mov eax,BLOCK
.mix:
    mov rsi,rax
    lea rdi,[mix_buffer]
    call audio_mix
    mov [pending],rax
    mov qword [pending_offset],0
.write:
    mov rdi,[pcm]
    lea rsi,[mix_buffer]
    mov rax,[pending_offset]
    lea rsi,[rsi+rax*2]
    mov rdx,[pending]
    call snd_pcm_writei wrt ..plt
    test rax,rax
    js .recover
    sub [pending],rax
    add [pending_offset],rax
    jmp .done
.recover:
    cmp eax,-11 ; EAGAIN: try retained buffer next frame
    je .done
    mov esi,eax
    mov rdi,[pcm]
    mov edx,1
    call snd_pcm_recover wrt ..plt
.done:
    pop rbp
.return:
    ret
; audio_shutdown() -> void; close outside update, no audio callback exists.
audio_shutdown:
    push rbp
    mov rbp,rsp
    mov rdi,[pcm]
    test rdi,rdi
    jz .done
    call snd_pcm_close wrt ..plt
.done:
    mov qword [pcm],0
    mov qword [sample_count],0
    mov qword [pending],0
    pop rbp
    ret
section .note.GNU-stack noalloc noexec nowrite progbits

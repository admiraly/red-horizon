#version 450 core
uniform sampler2D scene;
uniform float exposure;
uniform int passthrough;
layout(location=0) out vec4 outputColour;
vec3 encodeDisplay(vec3 linear){
 return mix(12.92*linear,1.055*pow(linear,vec3(1./2.4))-.055,greaterThan(linear,vec3(.0031308)));
}
void main(){
 vec3 radiance=max(texelFetch(scene,ivec2(gl_FragCoord.xy),0).rgb,vec3(0));
 if(passthrough!=0){outputColour=vec4(radiance,1);return;}
 radiance*=exposure;
 float luminance=dot(radiance,vec3(.2126,.7152,.0722));
 // Extended Reinhard with a fixed linear white point of four. Fixed exposure
 // avoids camera-driven pumping during flashes; automatic adaptation is absent.
 vec3 mapped=radiance*(1.+luminance/16.)/(1.+luminance);
 outputColour=vec4(encodeDisplay(clamp(mapped,0.,1.)),1);
}

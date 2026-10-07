#version 450 core
uniform sampler2D sourceImage;
uniform int pass;
layout(location=0) out vec4 outputColour;
vec3 sampleAt(ivec2 p){
 return max(texelFetch(sourceImage,clamp(p,ivec2(0),textureSize(sourceImage,0)-1),0).rgb,vec3(0));
}
void main(){
 ivec2 p=ivec2(gl_FragCoord.xy);
 if(pass==0){
  p*=2;
  vec3 c=(sampleAt(p)+sampleAt(p+ivec2(1,0))+sampleAt(p+ivec2(0,1))+sampleAt(p+ivec2(1,1)))*.25;
  float luminance=dot(c,vec3(.2126,.7152,.0722));
  outputColour=vec4(c*max(luminance-1.,0.)/max(luminance,.000001),1);
  return;
 }
 ivec2 axis=pass==1?ivec2(1,0):ivec2(0,1);
 const float weights[5]=float[5](.2270270270,.1945945946,.1216216216,.0540540541,.0162162162);
 vec3 c=sampleAt(p)*weights[0];
 for(int i=1;i<=4;i++)c+=(sampleAt(p+axis*i)+sampleAt(p-axis*i))*weights[i];
 outputColour=vec4(c,1);
}

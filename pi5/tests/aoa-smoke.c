/* Transport smoke test only. Does not claim full CarLife compatibility. */
#include <libusb-1.0/libusb.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
static int hold_seconds;
static libusb_device_handle *target(libusb_context *ctx, unsigned short pid) {
 libusb_device **list; ssize_t n=libusb_get_device_list(ctx,&list);
 libusb_device_handle *result=NULL;
 for(ssize_t i=0;i<n;i++) {
  struct libusb_device_descriptor d;
  if(libusb_get_device_descriptor(list[i],&d)||d.idVendor!=0x18d1||d.idProduct!=pid)continue;
  libusb_device_handle *h=NULL; if(libusb_open(list[i],&h))continue;
  unsigned char serial[256]={0};
  if(libusb_get_string_descriptor_ascii(h,d.iSerialNumber,serial,255)>0&&!strcmp((char*)serial,"cp2cl-pi5")){result=h;break;}
  libusb_close(h);
 }
 libusb_free_device_list(list,1);return result;
}

static unsigned char rx[1024*1024];
static size_t used=0;
static uint32_t be32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static void put32(unsigned char *p,uint32_t v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static int send_cmd(libusb_device_handle *h,int ep,uint32_t type,const unsigned char *body,int size){
 unsigned char outer[8],message[256];int done;
 if(size>248)return -1;
 put32(outer,1);put32(outer+4,8+size);
 message[0]=size>>8;message[1]=size;message[2]=message[3]=0;put32(message+4,type);
 if(size)memcpy(message+8,body,size);
 if(libusb_bulk_transfer(h,ep,outer,8,&done,3000)||done!=8)return -1;
 if(libusb_bulk_transfer(h,ep,message,8+size,&done,3000)||done!=8+size)return -1;
 return 0;
}
static int next_frame(libusb_device_handle *h,int ep,uint32_t *channel,uint32_t *type,unsigned char *body,int *bodylen){
 for(;;){
  if(used>=8){
   size_t len=be32(rx+4);*channel=be32(rx);size_t head=(*channel==1||*channel==6)?8:12;
   if(len<head||len>640*1024)return -1;
   if(used>=len+8){
    *type=be32(rx+8+head-4);*bodylen=len-head;
    if(body&&*bodylen<=256)memcpy(body,rx+8+head,*bodylen);
    if(*channel==2&&*type==0x20001&&getenv("CP2CL_CAPTURE_VIDEO")){
     FILE *f=fopen(getenv("CP2CL_CAPTURE_VIDEO"),"wb");
     if(!f)return -1;
     size_t written=fwrite(rx+8+head,1,*bodylen,f);fclose(f);
     if(written!=(size_t)*bodylen)return -1;
    }
    memmove(rx,rx+8+len,used-8-len);used-=8+len;return 0;
   }
  }
  int n=0;int r=libusb_bulk_transfer(h,ep,rx+used,65536,&n,4000);
  if(r||!n){fprintf(stderr,"bulk read: %s n=%d\n",libusb_error_name(r),n);return -1;}
  used+=n;if(used>sizeof(rx)-65536)return -1;
 }
}
static int expect_type(libusb_device_handle *h,int ep,uint32_t expected){
 for(int i=0;i<30;i++){
  uint32_t channel,type;unsigned char body[256];int n;
  if(next_frame(h,ep,&channel,&type,body,&n))return -1;
  printf("RX channel=%u type=%08x body_bytes=%d\n",channel,type,n);
  if(type==expected){
   if(expected==0x10008){unsigned char expected_body[]={0x08,0x80,0x0a,0x10,0xd0,0x05,0x18,0x1e};if(getenv("CP2CL_TEST_WIDE_60")){expected_body[2]=0x0f;expected_body[7]=0x3c;}if(n!=8||memcmp(body,expected_body,8))return -1;printf("VIDEO_INIT_ACK protobuf=");for(int j=0;j<n&&j<256;j++)printf("%02x",body[j]);puts("");}
   return 0;
  }
 }
 return -1;
}
static int protocol(libusb_device_handle *h,int iface,int in,int out){
 if(libusb_claim_interface(h,iface))return 1;
 const unsigned char version[]={0x08,0x03,0x10,0x00};
 if(send_cmd(h,out,0x18001,version,sizeof(version))||expect_type(h,in,0x10002))return 2;
 puts("CarLife protocol version 3.0 / MATCH_STATUS roundtrip PASS (synthetic Linux host)");
 if(send_cmd(h,out,0x18003,NULL,0)||expect_type(h,in,0x10004))return 5;
 puts("HU_INFO / MD_INFO roundtrip PASS; no authentication challenge performed");
 unsigned char video[]={0x08,0x80,0x0a,0x10,0xd0,0x05,0x18,0x1e};
 if(getenv("CP2CL_TEST_WIDE_60")){video[2]=0x0f;video[7]=0x3c;}
 if(send_cmd(h,out,0x18007,video,sizeof(video))||expect_type(h,in,0x10008))return 3;
 printf("Synthetic %s VIDEO_ENCODER_INIT roundtrip PASS; NTG6 negotiation NOT TESTED\n",getenv("CP2CL_TEST_WIDE_60")?"1920x720@60":"1280x720@30");
 if(send_cmd(h,out,0x18009,NULL,0)||expect_type(h,in,0x20001))return 4;
 puts("H.264 GUIDE frame received via USB PASS; this is not iPhone CarPlay video");
 if(hold_seconds){
  struct timespec start,now;clock_gettime(CLOCK_MONOTONIC,&start);
  unsigned long frames=0,video_frames=0;time_t reported=0;
  printf("PHONE TEST WINDOW OPEN seconds=%d; draining USB only, no video/audio saved\n",hold_seconds);
  for(;;){
   clock_gettime(CLOCK_MONOTONIC,&now);time_t elapsed=now.tv_sec-start.tv_sec;
   if(elapsed>=hold_seconds)break;
   uint32_t channel,type;int n;
   if(next_frame(h,in,&channel,&type,NULL,&n))return 6;
   frames++;if(channel==2&&type==0x20001)video_frames++;
   if(elapsed-reported>=10){printf("USB drain elapsed=%ld frames=%lu video_frames=%lu (includes guide)\n",(long)elapsed,frames,video_frames);reported=elapsed;}
  }
  puts("PHONE TEST WINDOW CLOSED");
 }
 libusb_release_interface(h,iface);return 0;
}

int main(void){
 setbuf(stdout,NULL);
 if(getenv("CP2CL_HOLD_SECONDS")){
  char *end;long n=strtol(getenv("CP2CL_HOLD_SECONDS"),&end,10);
  if(*end||n<1||n>1800||!getenv("CP2CL_TEST_PROTOCOL")||getenv("CP2CL_CAPTURE_VIDEO")){
   fputs("Hold requires protocol mode, 1..1800 seconds, and video capture disabled\n",stderr);return 1;
  }
  hold_seconds=(int)n;
 }
 libusb_context *ctx=NULL;if(libusb_init(&ctx))return 1;
 libusb_device_handle *h=target(ctx,0x4ee1);
 if(!h){fprintf(stderr,"Expected cp2cl-pi5 18d1:4ee1 not found\n");return 2;}
 unsigned char version[2];int r=libusb_control_transfer(h,0xc0,51,0,0,version,2,3000);
 if(r!=2||version[0]!=2||version[1]!=0){fprintf(stderr,"GET_PROTOCOL failed: %d\n",r);return 3;}
 puts("AOA GET_PROTOCOL=2 PASS");
 const char *strings[]={"Linux test host","CarLife smoke","USB transport test","1.0","https://github.com/0x5e/cp2cl","pi5-local-test"};
 for(int i=0;i<6;i++){
  r=libusb_control_transfer(h,0x40,52,0,i,(unsigned char*)strings[i],strlen(strings[i])+1,3000);
  if(r!=(int)strlen(strings[i])+1){fprintf(stderr,"SEND_STRING[%d] failed: %d\n",i,r);return 4;}
 }
 puts("AOA SEND_STRING x6 PASS");
 r=libusb_control_transfer(h,0x40,53,0,0,NULL,0,3000);
 printf("AOA START returned %d (%s); checking re-enumeration\n",r,libusb_error_name(r));
 libusb_close(h);h=NULL;
 for(int i=0;i<50;i++){usleep(100000);h=target(ctx,0x2d00);if(h)break;}
 if(!h){fprintf(stderr,"Accessory re-enumeration missing\n");return 5;}
 struct libusb_config_descriptor *config=NULL;
 if(libusb_get_active_config_descriptor(libusb_get_device(h),&config))return 6;
 int found=0,iface=0,in=0,out=0;
 for(int i=0;i<config->bNumInterfaces;i++){
  const struct libusb_interface_descriptor *d=&config->interface[i].altsetting[0];
  if(d->bInterfaceClass==0xff&&d->bNumEndpoints==2){
   printf("Accessory 18d1:2d00 interface=%d class=ff endpoints=%02x/%02x maxpacket=%u/%u\n",d->bInterfaceNumber,d->endpoint[0].bEndpointAddress,d->endpoint[1].bEndpointAddress,d->endpoint[0].wMaxPacketSize,d->endpoint[1].wMaxPacketSize);
   iface=d->bInterfaceNumber;in=d->endpoint[0].bEndpointAddress;out=d->endpoint[1].bEndpointAddress;
   found=(d->endpoint[0].bEndpointAddress&0x80)&&!(d->endpoint[1].bEndpointAddress&0x80);
  }
 }
 libusb_free_config_descriptor(config);
 int protocol_result=0;
 if(found&&getenv("CP2CL_TEST_PROTOCOL"))protocol_result=protocol(h,iface,in,out);
 libusb_close(h);libusb_exit(ctx);
 if(protocol_result){fprintf(stderr,"Protocol smoke failure stage=%d\n",protocol_result);return 10+protocol_result;}
 if(!found)return 7;
 puts("AOA re-enumeration and bulk descriptor ordering PASS; full CarLife/NTG6 interoperability NOT TESTED");return 0;
}
